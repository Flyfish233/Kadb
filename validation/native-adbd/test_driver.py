import unittest

from adb_observer import AdbRelay
from run_emulator import authenticated_connection_count, has_tcp_listener


class ExistingTransportTest(unittest.TestCase):
    def test_local_ipv4_and_ipv6_listener(self):
        for address in ("0.0.0.0:5555", "[::]:5555", "*:5555"):
            self.assertTrue(has_tcp_listener(f"LISTEN 0 4 {address} *:*\n", 5555))

    def test_foreign_port_and_connected_socket_cannot_prove_listener(self):
        self.assertFalse(has_tcp_listener("LISTEN 0 4 127.0.0.1:1234 127.0.0.1:5555\n", 5555))
        self.assertFalse(has_tcp_listener("ESTAB 0 0 127.0.0.1:5555 127.0.0.1:1234\n", 5555))
        self.assertFalse(has_tcp_listener("LISTEN 0 4 *:55550 *:*\n", 5555))
        self.assertFalse(has_tcp_listener("", 5555))

    def test_aggregate_auth_frames_do_not_prove_each_reconnection_authenticated(self):
        frames = {"adbd_to_host:AUTH:1": 3, "host_to_adbd:AUTH:2": 3, "adbd_to_host:CNXN": 3}
        self.assertEqual(1, authenticated_connection_count({"connection_counts": {"1": frames, "2": {}, "3": {}}}))
        self.assertEqual(3, authenticated_connection_count({"connection_counts": {str(n): frames for n in range(3)}}))
        self.assertEqual(0, authenticated_connection_count({"counts": frames}))

    def test_auth_reconnections_remain_observable_after_event_excerpt_limit(self):
        # A large Sync transfer fills the event excerpt before the reconnects.
        relay = AdbRelay(1)
        try:
            for _ in range(600):
                relay.record(1, "host_to_adbd", {"command": "WRTE", "arg0": 1})
            for connection in (1, 2, 3):
                relay.record(connection, "adbd_to_host", {"command": "AUTH", "arg0": 1})
                relay.record(connection, "host_to_adbd", {"command": "AUTH", "arg0": 2})
                relay.record(connection, "adbd_to_host", {"command": "CNXN", "arg0": 0})
            snapshot = relay.snapshot()
            self.assertEqual(512, len(snapshot["first_events"]))
            self.assertEqual(3, authenticated_connection_count(snapshot))
        finally:
            relay.server.server_close()


if __name__ == "__main__":
    unittest.main()
