"""Cross-platform portable collector safety, validation, and report contracts.

No real network, user identity, telemetry, process enumeration or admin privileges.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json
import unittest
from unittest.mock import patch

from opspulse import cli, portable
from opspulse.report_io import write_report


class FakePsutil:
    def __init__(self):
        self.events = []
        self.cpu = 24.0
        self.ram_available = 4 * 1024**3
        self.disk_used = 70 * 1024**3
        self.net = {"loopback": SimpleNamespace(isup=True), "lan": SimpleNamespace(isup=True)}

    def cpu_count(self, logical=True):
        self.events.append("cpu_count")
        return 8

    def cpu_percent(self, interval):
        self.events.append("cpu_percent")
        assert interval <= 0.25
        return self.cpu

    def virtual_memory(self):
        self.events.append("memory")
        return SimpleNamespace(total=16 * 1024**3, available=self.ram_available)

    def swap_memory(self):
        self.events.append("swap")
        return SimpleNamespace(total=4 * 1024**3, used=1024**3)

    def disk_usage(self, path):
        self.events.append("disk")
        assert path
        return SimpleNamespace(total=100 * 1024**3, used=self.disk_used, free=100 * 1024**3 - self.disk_used)

    def boot_time(self):
        self.events.append("boot")
        return 1_700_000_000

    def net_if_stats(self):
        self.events.append("net")
        return self.net


class PortableTests(unittest.TestCase):
    def test_windows_local_diagnostics_are_real_mode_and_no_network(self):
        ps = FakePsutil()
        with patch("opspulse.portable.time.time", return_value=1_700_864_000), \
             patch("opspulse.collector.socket.getaddrinfo", side_effect=AssertionError("unexpected DNS")), \
             patch("opspulse.collector.socket.create_connection", side_effect=AssertionError("unexpected TCP")):
            report = portable.collect_portable(psutil_module=ps, system_name="Windows")
        self.assertEqual(report["mode"], "LIVE LOCAL WINDOWS")
        self.assertEqual(report["schema_version"], "1.1")
        self.assertEqual(len(report["checks"]), 8)
        self.assertEqual(report["summary"]["skip"], 2)  # inodes + restore
        self.assertEqual([c["key"] for c in report["checks"]],
                         ["cpu_percent", "ram_portable", "swap_portable", "disk_portable",
                          "inodes", "uptime", "interfaces", "backup"])
        self.assertEqual(report["summary"]["critical"], 0)
        self.assertEqual(report["checks"][0]["value"], "24.0% sampled")
        self.assertIn("No external DNS/TCP probes", report["network_probes"])
        self.assertIn("cpu_percent", ps.events)
        self.assertNotIn("ip_address", json.dumps(report).lower())
        self.assertNotIn("mac_address", json.dumps(report).lower())

    def test_macos_default_and_no_linux_service_calls(self):
        ps = FakePsutil()
        with patch("opspulse.portable.time.time", return_value=1_700_864_000):
            report = portable.collect_portable(
                psutil_module=ps, system_name="Darwin", service_names=("sshd",))
        self.assertEqual(report["mode"], "LIVE LOCAL MACOS")
        self.assertEqual(report["summary"]["skip"], 3)
        service = [c for c in report["checks"] if c["key"] == "service"][0]
        self.assertEqual(service["status"], "skip")
        self.assertEqual(service["label"], "Requested service check")
        self.assertNotIn("sshd", json.dumps(report))

    def test_cpu_and_memory_thresholds(self):
        ps = FakePsutil()
        ps.cpu = 98
        ps.ram_available = 512 * 1024**2
        ps.disk_used = 93 * 1024**3
        with patch("opspulse.portable.time.time", return_value=1_700_864_000):
            report = portable.collect_portable(psutil_module=ps, system_name="Windows")
        self.assertEqual(report["summary"]["critical"], 2)
        self.assertEqual(report["summary"]["warn"], 1)
        self.assertEqual(report["action_plan"][0]["priority"], "critical")
        self.assertEqual(report["checks"][3]["value"], "93.0% used")

    def test_swap_is_information_and_inodes_not_falsely_failed(self):
        ps = FakePsutil()
        ps.swap_memory = lambda: SimpleNamespace(total=0, used=0)
        with patch("opspulse.portable.time.time", return_value=1_700_864_000):
            report = portable.collect_portable(psutil_module=ps, system_name="Darwin")
        self.assertEqual(report["checks"][2]["status"], "info")
        self.assertEqual(report["checks"][2]["value"], "Not configured")
        self.assertEqual(report["checks"][4]["status"], "skip")
        self.assertIn("not a Windows/macOS health failure", report["checks"][4]["detail"])

    def test_invalid_or_unavailable_data_remains_skipped_not_healthy(self):
        ps = FakePsutil()
        ps.cpu = -5.0
        ps.ram_available = 18 * 1024**3
        ps.disk_usage = lambda path: (_ for _ in ()).throw(PermissionError("denied"))
        with patch("opspulse.portable.time.time", return_value=1_700_864_000):
            report = portable.collect_portable(psutil_module=ps, system_name="Windows")
        for i in (0,1,3):
            self.assertEqual(report["checks"][i]["status"], "skip")

    def test_fake_no_interfaces_does_not_mean_security_scan(self):
        ps = FakePsutil()
        ps.net = {}
        with patch("opspulse.portable.time.time", return_value=1_700_864_000):
            report = portable.collect_portable(psutil_module=ps, system_name="Windows")
        interfaces = next(c for c in report["checks"] if c["key"] == "interfaces")
        self.assertEqual(interfaces["status"], "info")
        self.assertNotIn("lan", json.dumps(report))
        self.assertNotIn("loopback", json.dumps(report))

    def test_validation_platform_and_tcp_port(self):
        with self.assertRaises(RuntimeError):
            portable.collect_portable(psutil_module=FakePsutil(), system_name="FreeBSD")
        with self.assertRaises(ValueError):
            portable.collect_portable(psutil_module=FakePsutil(), system_name="Windows", tcp_port=65536)
        with self.assertRaises(ValueError):
            portable.collect_portable(psutil_module=FakePsutil(), system_name="Windows",
                                     service_names=tuple("s" for _ in range(11)))

    def test_missing_dependency_is_clear(self):
        import builtins
        old_import = builtins.__import__
        def block(name, *args, **kwargs):
            if name == "psutil":
                raise ImportError("no psutil")
            return old_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=block):
            with self.assertRaisesRegex(RuntimeError, "requirements-desktop.txt"):
                portable._psutil()

    def test_report_saves_locally_and_keeps_html_safe(self):
        with TemporaryDirectory() as d:
            report = portable.collect_portable(psutil_module=FakePsutil(), system_name="Windows")
            json_path, html_path = write_report(report, Path(d))
            self.assertTrue(html_path.exists())
            obj = json.loads(json_path.read_text())
            self.assertEqual(obj["mode"], "LIVE LOCAL WINDOWS")
            self.assertIn("Recommended troubleshooting next steps", html_path.read_text())
            self.assertNotIn('<script src=', html_path.read_text())

    def test_cli_routes_non_linux_platform_to_portable_collector(self):
        from opspulse.collector import demo_report
        with TemporaryDirectory() as d, \
             patch("opspulse.cli.sys.platform", "win32"), \
             patch("opspulse.cli.collect_portable", return_value=demo_report()) as collector:
            code = cli.main(["--out-dir", d])
            collector.assert_called_once()
            self.assertEqual(code, 0)

    def test_cli_still_runs_linux_implementation(self):
        from opspulse.collector import demo_report
        with TemporaryDirectory() as d, \
             patch("opspulse.cli.sys.platform", "linux"), \
             patch("opspulse.cli.collect", return_value=demo_report()) as collector:
            code = cli.main(["--out-dir", d])
            collector.assert_called_once()
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
