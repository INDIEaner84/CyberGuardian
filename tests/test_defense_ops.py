import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from core.defense_ops import DefenseOps


class DefenseOpsTests(unittest.TestCase):
    def setUp(self):
        self.ops = DefenseOps()
        self.interface = self.ops.interfaces()[0]

    def test_simulation_capture_is_bounded_and_metadata_only(self):
        with patch.object(DefenseOps, "_which", return_value=None):
            result = self.ops.capture_metadata(self.interface, duration=99, limit=99, preset="metadata")
        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "simulation")
        self.assertLessEqual(len(result["packets"]), 30)
        self.assertTrue(all(packet["synthetic"] for packet in result["packets"]))

    def test_mac_preview_never_mutates_interface(self):
        result = self.ops.mac_preview(self.interface)
        self.assertFalse(result["mutated"])
        self.assertEqual(len(result["proposed"].split(":")), 6)
        self.assertIn("Vorschau", result["warning"])

    def test_live_capture_requests_only_bounded_metadata(self):
        runner = Mock(return_value=SimpleNamespace(returncode=0, stdout="1.0|192.0.2.10|51834|192.0.2.1|443|TCP\n", stderr=""))
        ops = DefenseOps(command_runner=runner)

        def which(*commands):
            return "/usr/bin/tshark" if "tshark" in commands else None

        with patch.object(DefenseOps, "_which", side_effect=which):
            result = ops.capture_metadata(self.interface, duration=99, limit=99, preset="tcp")

        argv = runner.call_args.args[0]
        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "live-metadata")
        self.assertIn("-p", argv)  # no promiscuous mode
        self.assertIn("-T", argv)
        self.assertNotIn("-w", argv)  # never write a capture file/payload
        self.assertEqual(result["packets"][0]["protocol"], "TCP")

    def test_capture_profile_is_allowlisted(self):
        with self.assertRaises(ValueError):
            self.ops.capture_metadata(self.interface, preset="arbitrary shell text")

    def test_interface_names_are_validated(self):
        for name in ("eth0; rm -rf /", "$(reboot)", "a" * 40, "../../etc"):
            with self.assertRaises(ValueError):
                self.ops.capture_metadata(name)

    @staticmethod
    def _only(engine):
        def which(*commands):
            return f"/usr/bin/{engine}" if engine in commands else None
        return which

    def test_web_preset_covers_http_and_https(self):
        tshark = DefenseOps._capture_args("lo", 3, 5, "web", "tshark")
        self.assertEqual(tshark[tshark.index("-f") + 1], "tcp and ( port 80 or port 443 )")
        tcpdump = DefenseOps._capture_args("lo", 3, 5, "web", "tcpdump")
        self.assertIn("443", tcpdump)
        self.assertIn("80", tcpdump)

    def test_tshark_fields_include_udp_and_ipv6(self):
        argv = DefenseOps._capture_args("lo", 3, 5, "dns", "tshark")
        fields = [argv[index + 1] for index, value in enumerate(argv) if value == "-e"]
        for field in ("ipv6.src", "udp.srcport", "udp.dstport", "ipv6.dst"):
            self.assertIn(field, fields)
        packets = DefenseOps._parse_tshark(
            "1700000000.10|198.51.100.7|||41201|203.0.113.5|||53|DNS\n"
            "1700000000.35||2001:db8::1|51834|||2001:db8::2|443||TLSv1.3\n"
        )
        self.assertEqual(packets[0]["source_port"], "41201")
        self.assertEqual(packets[0]["destination_port"], "53")
        self.assertEqual(packets[1]["source"], "2001:db8::1")
        self.assertEqual(packets[1]["time"], "+0.250s")

    def test_tcpdump_lines_are_reduced_to_header_metadata(self):
        raw = (
            "1700000000.100000 IP 192.0.2.10.51834 > 192.0.2.1.443: Flags [S], seq 1, win 64240, length 0\n"
            "1700000000.350000 IP 192.0.2.10.41201 > 192.0.2.53.53: 12345+ A? secret-host.example. (29)\n"
            "1700000000.400000 IP 192.0.2.10 > 192.0.2.1: ICMP echo request, id 1, seq 1, length 64\n"
            "1700000000.500000 IP6 2001:db8::1.51834 > 2001:db8::2.443: Flags [P.], seq 1:20, length 19\n"
            "1700000000.600000 ARP, Request who-has 192.0.2.1 tell 192.0.2.10, length 28\n"
            "1700000000.700000 lo    In  IP 127.0.0.1.52000 > 127.0.0.1.4173: Flags [S], seq 0, length 0\n"
            "tcpdump: listening on lo, link-type EN10MB\n"
        )
        packets = DefenseOps._parse_tcpdump(raw)
        self.assertEqual([packet["protocol"] for packet in packets], ["TCP", "DNS", "ICMP", "TCP", "ARP", "TCP"])
        self.assertEqual((packets[0]["source"], packets[0]["source_port"]), ("192.0.2.10", "51834"))
        self.assertEqual((packets[0]["destination"], packets[0]["destination_port"]), ("192.0.2.1", "443"))
        self.assertEqual(packets[2]["source_port"], "")
        self.assertEqual((packets[3]["source"], packets[3]["destination_port"]), ("2001:db8::1", "443"))
        self.assertEqual((packets[4]["source"], packets[4]["destination"]), ("192.0.2.10", "192.0.2.1"))
        self.assertEqual(packets[5]["destination_port"], "4173")
        self.assertEqual(packets[1]["time"], "+0.250s")
        self.assertNotIn("secret-host", repr(packets))  # DNS names/payload details are dropped

    def test_tcpdump_capture_window_keeps_partial_output(self):
        partial = b"1700000000.100000 IP 192.0.2.10.51834 > 192.0.2.1.443: Flags [S], seq 1, length 0\n"
        runner = Mock(side_effect=subprocess.TimeoutExpired(["tcpdump"], 3, output=partial))
        ops = DefenseOps(command_runner=runner)
        with patch.object(DefenseOps, "_which", side_effect=self._only("tcpdump")):
            result = ops.capture_metadata(self.interface, duration=3, limit=5, preset="tcp")
        self.assertEqual(runner.call_args.kwargs["timeout"], 3)
        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "live-metadata")
        self.assertEqual(len(result["packets"]), 1)
        self.assertEqual(result["packets"][0]["destination_port"], "443")

    def test_failed_capture_reports_error_without_packets(self):
        runner = Mock(return_value=SimpleNamespace(returncode=1, stdout="", stderr="permission denied"))
        ops = DefenseOps(command_runner=runner)
        with patch.object(DefenseOps, "_which", side_effect=self._only("tshark")):
            result = ops.capture_metadata(self.interface, duration=1, limit=1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["packets"], [])
        self.assertIn("permission denied", result["error"])


if __name__ == "__main__":
    unittest.main()
