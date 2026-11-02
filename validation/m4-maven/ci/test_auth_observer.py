#!/usr/bin/env python3
"""Focused parser and real-socket checks; not evidence of Android behavior."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import unittest

from auth_observer import AdbRsaPublicKey, AuthFrameObserver, AuthRelay, AuthSession


def frame(command, payload=b"", arg0=0, arg1=0):
    value = int.from_bytes(command, "little")
    return struct.pack("<6I", value, arg0, arg1, len(payload), sum(payload), value ^ 0xFFFFFFFF) + payload


def public_blob(modulus):
    # The Montgomery fields are irrelevant to independent Python RSA verify.
    # Include the authentic values so this fixture is also a valid ADB key.
    n0inv = (-pow(modulus & 0xFFFFFFFF, -1, 1 << 32)) % (1 << 32)
    rr = pow(2, 4096, modulus)
    raw = struct.pack("<II", 64, n0inv) + modulus.to_bytes(256, "little") + rr.to_bytes(256, "little") + struct.pack("<I", 65537)
    return base64.b64encode(raw).decode("ascii")


@unittest.skipUnless(shutil.which("openssl"), "OpenSSL is required for the independent RSA signature fixture")
class AuthObserverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="kadb-m4-observer-test-")
        root = Path(cls.directory.name)
        cls.key_path = root / "temporary-rsa.pem"
        subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(cls.key_path)], check=True, capture_output=True)
        cls.key_path.chmod(0o600)
        result = subprocess.run(["openssl", "rsa", "-in", str(cls.key_path), "-modulus", "-noout"], check=True, capture_output=True, text=True)
        modulus = int(result.stdout.strip().split("=", 1)[1], 16)
        cls.blob = public_blob(modulus)
        cls.public = AdbRsaPublicKey(cls.blob)
        cls.token = hashlib.sha1(b"independent OpenSSL M4 signature fixture").digest()
        token_path = root / "token"
        token_path.write_bytes(cls.token)
        signed = subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(cls.key_path), "-pkeyopt", "digest:sha1", "-in", str(token_path)], check=True, capture_output=True)
        cls.signature = signed.stdout

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def observers(self):
        session = AuthSession(self.public)
        events = []
        host = AuthFrameObserver("host_to_adbd", events.append, session)
        device = AuthFrameObserver("adbd_to_host", events.append, session)
        return session, events, host, device

    def test_openssl_prehashed_signature_and_wrong_identity(self):
        self.assertTrue(self.public.verifies(self.token, self.signature))
        self.assertFalse(self.public.verifies(hashlib.sha1(self.token).digest(), self.signature))
        self.assertFalse(self.public.verifies(self.token, self.signature[:-1]))
        self.assertFalse(self.public.verifies(self.token, self.signature[:-1] + bytes([self.signature[-1] ^ 1])))
        wrong = AdbRsaPublicKey(public_blob(self.public.modulus ^ 2))
        self.assertFalse(wrong.verifies(self.token, self.signature))

    def test_fragmented_actual_signature_association_without_payload_leak(self):
        session, events, host, device = self.observers()
        wire = frame(b"AUTH", self.token, 1)
        for byte in wire:
            device.feed(bytes([byte]))
        wire = frame(b"AUTH", self.signature, 2)
        for start in range(0, len(wire), 7):
            host.feed(wire[start:start + 7])
        device.feed(frame(b"CNXN", b"device::features=shell_v2;", 0x01000001, 1024 * 1024))
        check = session.verifications[0]
        self.assertTrue(check["signature_matches_expected_identity"])
        self.assertTrue(check["token_observed_on_this_connection"])
        self.assertEqual(check["challenge_sequence"], 1)
        self.assertEqual(check["token_sha256"], hashlib.sha256(self.token).hexdigest())
        self.assertEqual([e["command"] for e in events], ["AUTH", "AUTH", "CNXN"])
        safe_report = json.dumps({"auth": session.events, "verified": session.verifications, "headers": events})
        for secret in [self.blob, self.token.hex(), self.signature.hex(), self.key_path.read_text()]:
            self.assertNotIn(secret, safe_report)
        self.assertEqual(session.token, bytearray())

    def test_challenge_is_not_inherited_by_another_signature_or_connection(self):
        session, events, host, device = self.observers()
        device.feed(frame(b"AUTH", self.token, 1))
        host.feed(frame(b"AUTH", self.signature, 2))
        host.feed(frame(b"AUTH", self.signature, 2))
        self.assertFalse(session.verifications[1]["signature_matches_expected_identity"])
        self.assertFalse(session.verifications[1]["token_observed_on_this_connection"])
        other, _, other_host, _ = self.observers()
        other_host.feed(frame(b"AUTH", self.signature, 2))
        self.assertFalse(other.verifications[0]["signature_matches_expected_identity"])

    def test_subsequent_challenge_replaces_previous_one(self):
        session, _, host, device = self.observers()
        device.feed(frame(b"AUTH", self.token, 1))
        device.feed(frame(b"AUTH", b"x" * 20, 1))
        host.feed(frame(b"AUTH", self.signature, 2))
        self.assertEqual(session.verifications[0]["challenge_sequence"], 2)
        self.assertFalse(session.verifications[0]["signature_matches_expected_identity"])

    def test_public_key_submission_is_fingerprint_only(self):
        session, _, host, _ = self.observers()
        host.feed(frame(b"AUTH", (self.blob + " temporary@fixture\0").encode("ascii"), 3))
        self.assertTrue(session.events[0]["public_key_matches_expected_identity"])
        self.assertNotIn(self.blob, json.dumps(session.events))

    def test_stls_transition_same_buffer_and_tls_payload_is_not_adb(self):
        session, events, host, device = self.observers()
        hello = b"\x03\x03" + b"r" * 32 + b"\x00\x13\x01\x00\x00\x06\x00\x2b\x00\x02\x03\x04"
        handshake = b"\x02" + len(hello).to_bytes(3, "big") + hello
        record = b"\x16\x03\x03" + len(handshake).to_bytes(2, "big") + handshake
        opaque_payload = frame(b"CNXN", b"must-not-be-observed")
        opaque = b"\x17\x03\x03" + len(opaque_payload).to_bytes(2, "big") + opaque_payload
        device.feed(frame(b"STLS", arg0=0x01000000) + record[:3])
        device.feed(record[3:] + opaque)
        self.assertEqual([e["command"] for e in events], ["STLS"])
        observed = device.snapshot()
        self.assertEqual(observed["server_hello"], [{"selected_version": 0x304, "cipher_suite": 0x1301}])
        self.assertEqual(observed["tls_record_counts"], {"22": 1, "23": 1})
        self.assertFalse(observed["tls_handshake_success_inferred"])
        self.assertNotIn("must-not-be-observed", json.dumps(observed))

    def test_malformed_and_oversized_input_is_bounded(self):
        session, events, host, device = self.observers()
        host.feed(frame(b"AUTH", b"x" * 9000, 3))
        self.assertEqual(host.payload, bytearray())
        self.assertIn({"error": "oversized_auth_payload"}, events)
        device.feed(frame(b"STLS") + b"\x16\x03\x03\xff\xff" + b"x" * 50000)
        self.assertIn("invalid_tls_record_header", device.snapshot()["tls_parse_errors"])
        self.assertEqual(device.tls.buffer, bytearray())
        self.assertEqual(device.tls.handshake, bytearray())

    def test_real_socket_relay_is_byte_transparent_and_records_eof(self):
        target = socket.socket()
        target.bind(("127.0.0.1", 0))
        target.listen(1)
        target_port = target.getsockname()[1]
        received = []
        failures = []
        challenge = frame(b"AUTH", self.token, 1)
        signature = frame(b"AUTH", self.signature, 2)
        cnxn = frame(b"CNXN", b"device::features=shell_v2;", 0x01000001, 1024 * 1024)

        def receive_exact(sock, length):
            value = bytearray()
            while len(value) < length:
                part = sock.recv(length - len(value))
                if not part:
                    raise RuntimeError("Unexpected fixture EOF")
                value.extend(part)
            return bytes(value)

        def peer():
            try:
                connection, _ = target.accept()
                with connection:
                    connection.settimeout(3)
                    connection.sendall(challenge)
                    received.append(receive_exact(connection, len(signature)))
                    connection.sendall(cnxn)
            except Exception as error:
                failures.append(type(error).__name__)
            finally:
                target.close()

        thread = threading.Thread(target=peer)
        thread.start()
        relay = AuthRelay(target_port, self.blob)
        with relay:
            with socket.create_connection(("127.0.0.1", relay.port), timeout=3) as client:
                self.assertEqual(receive_exact(client, len(challenge)), challenge)
                client.sendall(signature)
                self.assertEqual(receive_exact(client, len(cnxn)), cnxn)
                self.assertEqual(client.recv(1), b"")
        thread.join(timeout=3)
        self.assertEqual(failures, [])
        self.assertEqual(received, [signature])
        observed = relay.snapshot()
        self.assertEqual(observed["connections"], 1)
        self.assertEqual(observed["active_connections"], 0)
        self.assertTrue(observed["auth_verifications"]["1"][0]["signature_matches_expected_identity"])
        self.assertEqual(observed["counts"]["adbd_to_host:CNXN"], 1)
        self.assertTrue(any(e["event"] == "eof" and e["direction"] == "adbd_to_host" for e in observed["transport_events"]))

    def test_closed_target_does_not_produce_auth_evidence(self):
        closed = socket.socket()
        closed.bind(("127.0.0.1", 0))
        port = closed.getsockname()[1]
        closed.close()
        relay = AuthRelay(port, self.blob)
        with relay:
            with socket.create_connection(("127.0.0.1", relay.port), timeout=3) as client:
                self.assertEqual(client.recv(1), b"")
        observed = relay.snapshot()
        self.assertEqual(observed["counts"], {})
        self.assertEqual(observed["auth_verifications"], {"1": []})
        self.assertTrue(any(e["event"] == "transport_error" and e["stage"] == "connect" for e in observed["transport_events"]))


if __name__ == "__main__":
    unittest.main()
