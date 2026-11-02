#!/usr/bin/env python3
"""Byte-transparent, loopback-only AUTH/STLS evidence for the M4 emulator.

RSA token/signature payloads are inspected in memory and never included in a
report. The verifier uses only the supplied temporary identity's public key.
TLS records are not decrypted; a ServerHello is negotiation evidence, not proof
of certificate verification or successful authentication.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
from pathlib import Path
import select
import socket
import struct
import sys
import threading
import time

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "validation/native-adbd"))
from adb_observer import AdbRelay, FrameObserver  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "kadb_m3_tls_metadata", REPO / "validation/m3-maven/ci/run_pairing.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
TlsMetadata = _module.TlsMetadata

SHA1_DIGEST_INFO = bytes.fromhex("3021300906052b0e03021a05000414")
EVENT_LIMIT = 512


class AdbRsaPublicKey:
    """Decode Android's RSA-2048 public-key wire format, not an X.509 key."""

    def __init__(self, public_key_blob: str):
        fields = public_key_blob.strip().split()
        if not fields:
            raise ValueError("Empty ADB public key")
        try:
            raw = base64.b64decode(fields[0], validate=True)
        except (ValueError, TypeError) as error:
            raise ValueError("Malformed ADB public key encoding") from error
        if len(raw) != 524 or struct.unpack_from("<I", raw)[0] != 64:
            raise ValueError("Expected the 524-byte ADB RSA-2048 public key")
        self.modulus = int.from_bytes(raw[8:264], "little")
        self.exponent = struct.unpack_from("<I", raw, 520)[0]
        if self.modulus.bit_length() != 2048 or not self.modulus & 1:
            raise ValueError("Invalid ADB RSA-2048 modulus")
        if self.exponent < 3 or not self.exponent & 1:
            raise ValueError("Invalid ADB RSA public exponent")
        self.sha256 = hashlib.sha256(raw).hexdigest()

    def verifies(self, token: bytes, signature: bytes) -> bool:
        # ADB supplies an already hashed, 20-byte challenge. Hashing it again
        # would verify a different message from RSA_sign(NID_sha1, token, ...).
        if len(token) != 20 or len(signature) != 256:
            return False
        value = int.from_bytes(signature, "big")
        if value >= self.modulus:
            return False
        encoded = pow(value, self.exponent, self.modulus).to_bytes(256, "big")
        tail = SHA1_DIGEST_INFO + token
        expected = b"\x00\x01" + b"\xff" * (253 - len(tail)) + b"\x00" + tail
        return encoded == expected


class AuthSession:
    """One connection's challenge ownership, with report-safe observations."""

    def __init__(self, public_key: AdbRsaPublicKey):
        self.public_key = public_key
        self.token = bytearray()
        self.challenge_sequence = 0
        self.events = []
        self.verifications = []

    def _append(self, event):
        if len(self.events) < EVENT_LIMIT:
            self.events.append(event)

    def observe(self, direction: str, kind: int, payload: bytes):
        event = {"direction": direction, "auth_type": kind,
                 "payload_length": len(payload),
                 "payload_sha256": hashlib.sha256(payload).hexdigest()}
        if direction == "adbd_to_host" and kind == 1:
            self.clear_token()
            self.challenge_sequence += 1
            event["challenge_sequence"] = self.challenge_sequence
            event["valid_token_length"] = len(payload) == 20
            if len(payload) == 20:
                self.token.extend(payload)
        elif direction == "host_to_adbd" and kind == 2:
            verification = {
                "challenge_sequence": self.challenge_sequence,
                "token_observed_on_this_connection": len(self.token) == 20,
                "token_sha256": hashlib.sha256(self.token).hexdigest() if self.token else None,
                "token_length": len(self.token),
                "signature_sha256": event["payload_sha256"],
                "signature_length": len(payload),
                "expected_public_key_sha256": self.public_key.sha256,
                "signature_matches_expected_identity": self.public_key.verifies(bytes(self.token), payload),
                "scheme": "RSA-2048-PKCS1-v1_5-SHA1-prehashed",
            }
            if len(self.verifications) < EVENT_LIMIT:
                self.verifications.append(verification)
            event["signature_matches_expected_identity"] = verification["signature_matches_expected_identity"]
            event["challenge_sequence"] = self.challenge_sequence
            # A second signature without a new challenge must not inherit the
            # previous challenge's validity, even if the bytes happen to match.
            self.clear_token()
        elif direction == "host_to_adbd" and kind == 3:
            try:
                key_text = payload.rstrip(b"\x00").decode("ascii")
                supplied = AdbRsaPublicKey(key_text)
                event["public_key_matches_expected_identity"] = supplied.sha256 == self.public_key.sha256
                event["supplied_public_key_sha256"] = supplied.sha256
            except (UnicodeDecodeError, ValueError):
                event["public_key_matches_expected_identity"] = False
                event["malformed_public_key"] = True
        self._append(event)

    def clear_token(self):
        self.token[:] = b"\x00" * len(self.token)
        self.token.clear()


class AuthFrameObserver:
    """Fragment-safe ADB frames, then public TLS metadata after STLS."""

    def __init__(self, direction, record, session: AuthSession):
        self.direction = direction
        self.record = record
        self.session = session
        self.header = bytearray()
        self.remaining = 0
        self.command = None
        self.auth_type = None
        self.payload = bytearray()
        self.capture_auth = False
        self.tls_active = False
        self.invalid = False
        self.tls = TlsMetadata()

    def feed(self, data: bytes):
        while data and not self.invalid:
            if self.tls_active:
                # Only the reusable, bounded record/ServerHello parser sees
                # these bytes. Its snapshot exposes no record payloads.
                self.tls.feed(data)
                del self.tls.negotiated[EVENT_LIMIT:]
                if self.tls.errors:
                    self.invalid = True
                    self.tls.buffer.clear()
                    self.tls.handshake.clear()
                return
            if self.remaining:
                size = min(len(data), self.remaining)
                if self.capture_auth:
                    self.payload.extend(data[:size])
                self.remaining -= size
                data = data[size:]
                if not self.remaining:
                    self._end_frame()
                continue
            size = min(24 - len(self.header), len(data))
            self.header.extend(data[:size])
            data = data[size:]
            if len(self.header) != 24:
                continue
            command, arg0, arg1, length, checksum, magic = struct.unpack("<6I", self.header)
            command_bytes = bytes(self.header[:4])
            self.header.clear()
            if magic != command ^ 0xFFFFFFFF or command_bytes not in FrameObserver.COMMANDS or length > 16 * 1024 * 1024:
                self.record({"error": "invalid_plaintext_adb_header"})
                self.invalid = True
                return
            self.command = command_bytes
            self.auth_type = arg0
            self.record({"command": command_bytes.decode("ascii"), "arg0": arg0,
                         "arg1": arg1, "payload_length": length})
            self.capture_auth = command_bytes == b"AUTH" and length <= 8192
            if command_bytes == b"AUTH" and not self.capture_auth:
                self.record({"error": "oversized_auth_payload"})
            if command_bytes == b"STLS" and length != 0:
                self.record({"error": "unexpected_stls_payload"})
            self.remaining = length
            if not self.remaining:
                self._end_frame()

    def _end_frame(self):
        if self.capture_auth:
            self.session.observe(self.direction, self.auth_type, bytes(self.payload))
            self.payload[:] = b"\x00" * len(self.payload)
            self.payload.clear()
        if self.command == b"STLS":
            self.tls_active = True
        self.capture_auth = False
        self.command = None

    def close(self):
        self.payload[:] = b"\x00" * len(self.payload)
        self.payload.clear()
        self.tls.buffer.clear()
        self.tls.handshake.clear()

    def snapshot(self):
        return {"stls_observed": self.tls_active,
                "tls_record_counts": dict(self.tls.records),
                "server_hello": copy.deepcopy(self.tls.negotiated),
                "tls_parse_errors": list(self.tls.errors),
                "tls_handshake_success_inferred": False}


class AuthRelay(AdbRelay):
    """M3 relay transport with actual per-connection AUTH and STLS evidence."""

    def __init__(self, target_port: int, public_key_blob: str):
        if not 1 <= target_port <= 65535:
            raise ValueError("Invalid target port")
        self.public_key = AdbRsaPublicKey(public_key_blob)
        super().__init__(target_port)
        self.lock = threading.RLock()
        self.sessions = {}
        self.observers = {}
        self.transport_events = []
        self.active_connections = 0
        self.idle = threading.Event()
        self.idle.set()
        self.started = time.monotonic()

    def transport(self, connection, event, **details):
        with self.lock:
            if len(self.transport_events) < EVENT_LIMIT:
                self.transport_events.append({"connection": connection, "event": event,
                                              "elapsed_ms": round((time.monotonic() - self.started) * 1000),
                                              **details})

    def handle(self, incoming: socket.socket):
        outgoing = None
        stage, direction = "connect", None
        with self.lock:
            self.connections += 1
            connection = self.connections
            self.active_connections += 1
            self.idle.clear()
            self.sockets.add(incoming)
            session = AuthSession(self.public_key)
            self.sessions[connection] = session
        self.transport(connection, "client_accepted")
        try:
            outgoing = socket.create_connection(("127.0.0.1", self.target_port), timeout=5)
            # Bounded sendall/recv; an idle connection is still owned by the
            # consumer's timeout or context shutdown, not an auth verdict.
            incoming.settimeout(10)
            outgoing.settimeout(10)
            self.transport(connection, "target_connected")
            with self.lock:
                self.sockets.add(outgoing)
            peers = {incoming: outgoing, outgoing: incoming}
            directions = {incoming: "host_to_adbd", outgoing: "adbd_to_host"}
            observers = {
                endpoint: AuthFrameObserver(value, lambda event, value=value: self.record(connection, value, event), session)
                for endpoint, value in directions.items()
            }
            with self.lock:
                self.observers[connection] = {directions[endpoint]: observer for endpoint, observer in observers.items()}
            readable = list(peers)
            while readable:
                stage, direction = "select", None
                ready, _, _ = select.select(readable, [], [], 0.5)
                for source in ready:
                    stage, direction = "read", directions[source]
                    data = source.recv(65536)
                    if not data:
                        self.transport(connection, "eof", direction=direction)
                        readable.remove(source)
                        try:
                            peers[source].shutdown(socket.SHUT_WR)
                        except OSError:
                            pass
                        continue
                    with self.lock:
                        observers[source].feed(data)
                    stage = "forward"
                    peers[source].sendall(data)
                    with self.lock:
                        self.byte_counts[direction] += len(data)
        except (OSError, ValueError) as error:
            self.transport(connection, "transport_error", stage=stage, direction=direction,
                           error_type=type(error).__name__, errno=getattr(error, "errno", None))
        finally:
            with self.lock:
                session.clear_token()
                for observer in self.observers.get(connection, {}).values():
                    observer.close()
            for endpoint in (incoming, outgoing):
                if endpoint is not None:
                    with self.lock:
                        self.sockets.discard(endpoint)
                    endpoint.close()
            self.transport(connection, "connection_closed")
            with self.lock:
                self.active_connections -= 1
                if not self.active_connections:
                    self.idle.set()

    def __exit__(self, *arguments):
        super().__exit__(*arguments)
        self.idle.wait(timeout=3)

    def snapshot(self):
        with self.lock:
            result = super().snapshot()
            result.update({
                "expected_public_key_sha256": self.public_key.sha256,
                "auth_events": {str(connection): copy.deepcopy(session.events)
                                for connection, session in self.sessions.items()},
                "auth_verifications": {str(connection): copy.deepcopy(session.verifications)
                                       for connection, session in self.sessions.items()},
                "tls": {str(connection): {direction: observer.snapshot() for direction, observer in observers.items()}
                        for connection, observers in self.observers.items()},
                "transport_events": copy.deepcopy(self.transport_events),
                "active_connections": self.active_connections,
                "raw_auth_payloads_persisted": False,
                "tls_payloads_decrypted": False,
                "authentication_verdict": "requires_adbd_and_consumer_cross_evidence",
            })
            return result
