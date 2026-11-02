"""Guard the observed boot-before-network race without retrying pairing sessions."""

import unittest

from wait_ready import network_readiness


ROUTES = """default via 10.0.2.2 dev wlan0 table 1016 proto static
10.0.2.0/24 dev wlan0 table 1016 proto static scope link
127.0.0.0/8 dev lo table local proto kernel scope host src 127.0.0.1
"""


class NetworkReadinessTests(unittest.TestCase):
    def test_boot_without_active_default_network_cannot_pass(self):
        for state in ("", "Active default network: none\n", "Active default network: 0\n"):
            self.assertIsNone(network_readiness(state, ROUTES))

    def test_default_network_without_usable_host_routes_cannot_pass(self):
        for routes in ("", ROUTES.splitlines()[0] + "\n", ROUTES.splitlines()[1] + "\n",
                       ROUTES.replace("10.0.2.2", "10.0.9.2"),
                       ROUTES.replace("default via 10.0.2.2 dev wlan0", "default via 10.0.2.2 dev wlan0 linkdown"),
                       ROUTES.replace("scope link", "scope link linkdown"),
                       ROUTES.replace("10.0.2.0/24 dev wlan0", "10.0.2.0/24 dev eth0")):
            self.assertIsNone(network_readiness("Active default network: 100\n", routes))

    def test_records_actual_default_and_on_link_route(self):
        result = network_readiness("  Active default network: 100\n", ROUTES)
        self.assertEqual(100, result["active_default_network"])
        self.assertEqual("10.0.2.2", result["host_alias"])
        self.assertEqual("wlan0", result["interface"])
        self.assertEqual(ROUTES.splitlines()[0], result["default_route"])
        self.assertEqual(ROUTES.splitlines()[1], result["on_link_route"])


if __name__ == "__main__":
    unittest.main()
