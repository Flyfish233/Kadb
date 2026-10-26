import struct
import socket
import threading
import unittest

from adb_observer import AdbRelay, FrameObserver


def frame(command: bytes, payload: bytes = b"", arg0: int = 0) -> bytes:
    number = int.from_bytes(command, "little")
    return struct.pack("<6I", number, arg0, 0, len(payload), sum(payload), number ^ 0xFFFFFFFF) + payload


class FrameObserverTest(unittest.TestCase):
    def test_fragmented_and_coalesced_frames(self):
        observed = []
        observer = FrameObserver(observed.append)
        transcript = frame(b"CNXN", b"host::\0") + frame(b"AUTH", b"a" * 20, 1) + frame(b"AUTH", b"b" * 256, 2)
        for index in range(0, len(transcript), 7):
            observer.feed(transcript[index:index + 7])
        self.assertEqual([(x["command"], x["arg0"]) for x in observed], [("CNXN", 0), ("AUTH", 1), ("AUTH", 2)])

    def test_payload_cannot_create_false_auth_evidence(self):
        observed = []
        observer = FrameObserver(observed.append)
        observer.feed(frame(b"WRTE", frame(b"AUTH", b"fake", 2)) + frame(b"OKAY"))
        self.assertEqual([x["command"] for x in observed], ["WRTE", "OKAY"])

    def test_tls_switch_stops_plaintext_observation(self):
        observed = []
        observer = FrameObserver(observed.append)
        observer.feed(frame(b"STLS") + b"\x16\x03\x03" + frame(b"AUTH", b"not-an-adb-header", 2))
        self.assertEqual([x["command"] for x in observed], ["STLS"])

    def test_invalid_magic_is_not_a_handshake(self):
        observed = []
        observer = FrameObserver(observed.append)
        invalid = bytearray(frame(b"AUTH", b"fake", 2))
        invalid[20] ^= 1
        observer.feed(invalid + frame(b"CNXN"))
        self.assertEqual(observed, [{"error": "invalid_plaintext_adb_header"}])

    def test_relay_preserves_large_payload_and_half_close(self):
        payload = bytes(range(256)) * 4096 + b"end-of-stream"
        request = frame(b"CNXN", b"host::\0") + frame(b"WRTE", payload)
        response = frame(b"CNXN", b"device::\0") + frame(b"WRTE", payload[::-1])
        received = bytearray()
        with socket.socket() as server:
            server.bind(("127.0.0.1", 0))
            server.listen(1)
            server.settimeout(5)

            def peer():
                connection, _ = server.accept()
                with connection:
                    connection.settimeout(5)
                    while data := connection.recv(997):
                        received.extend(data)
                    connection.sendall(response)

            worker = threading.Thread(target=peer, daemon=True)
            worker.start()
            with AdbRelay(server.getsockname()[1]) as relay:
                with socket.create_connection(("127.0.0.1", relay.port), timeout=5) as client:
                    client.sendall(request)
                    client.shutdown(socket.SHUT_WR)
                    answer = bytearray()
                    while data := client.recv(1231):
                        answer.extend(data)
            worker.join(timeout=5)
            self.assertFalse(worker.is_alive())
            self.assertEqual(received, request)
            self.assertEqual(answer, response)
            self.assertEqual(relay.snapshot()["counts"], {
                "host_to_adbd:CNXN": 1, "host_to_adbd:WRTE": 1,
                "adbd_to_host:CNXN": 1, "adbd_to_host:WRTE": 1,
            })


if __name__ == "__main__":
    unittest.main()
