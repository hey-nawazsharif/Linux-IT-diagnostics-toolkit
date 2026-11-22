"""No internet, no root, no external dependencies for tests."""
import contextlib
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from opspulse import collector
from opspulse import cli
from opspulse.render import render_html


class MemoryTests(unittest.TestCase):
    def test_memory_warning(self):
        with TemporaryDirectory() as d:
            f = Path(d) / "meminfo"
            f.write_text("MemTotal:       100000 kB\nMemAvailable:    8000 kB\n", encoding="ascii")
            c = collector.memory_check(f)
            self.assertEqual(c["status"], "warn")
            self.assertIn("92.0%", c["value"])

    def test_memory_critical(self):
        with TemporaryDirectory() as d:
            f = Path(d) / "meminfo"
            f.write_text("MemTotal:       100000 kB\nMemAvailable:    2000 kB\n", encoding="ascii")
            self.assertEqual(collector.memory_check(f)["status"], "critical")

    def test_missing_meminfo_skipped(self):
        self.assertEqual(collector.memory_check(Path("/nonexistent-ps-meminfo"))["status"], "skip")

    def test_invalid_meminfo_skipped(self):
        with TemporaryDirectory() as d:
            f = Path(d) / "meminfo"
            f.write_text("MemTotal: 1000 kB\nMemAvailable: 2000 kB\n", encoding="ascii")
            self.assertEqual(collector.memory_check(f)["status"], "skip")


class SafetyTests(unittest.TestCase):
    def test_demo_is_explicit_and_not_a_live_measurement(self):
        r = collector.demo_report()
        self.assertEqual(r["mode"], "SIMULATED DEMO")
        self.assertEqual(r["summary"]["warn"], 1)
        self.assertIn("SIMULATED", r["network_probes"])
        self.assertEqual(len(r["checks"]), 8)

    def test_no_network_probe_by_default(self):
        with patch.object(collector.socket, "getaddrinfo", side_effect=AssertionError("DNS called")), \
             patch.object(collector.socket, "create_connection", side_effect=AssertionError("TCP called")), \
             patch.object(collector.subprocess, "run", side_effect=AssertionError("systemctl called")):
            result = collector.collect() if __import__("sys").platform == "linux" else collector.demo_report()
            self.assertEqual(result["summary"]["skip"], 1)

    def test_service_name_sanitisation(self):
        with self.assertRaises(ValueError):
            collector.service_check("sshd;curl bad.example")

    def test_dns_injection_not_run_as_shell(self):
        def fake_resolver(host, port, **kwargs):
            self.assertEqual(host, "example.com")
            self.assertEqual(port, 443)
            return [(None,)]
        self.assertEqual(collector.dns_check("example.com", resolver=fake_resolver)["status"], "pass")

    def test_cpu_is_not_reported_as_percent(self):
        with patch.object(collector.os, "cpu_count", return_value=4), patch.object(collector.os, "getloadavg", return_value=(2.0, 1.0, 1.0)):
            c = collector.cpu_check()
        self.assertEqual(c["status"], "pass")
        self.assertNotIn("utilization percent.", c["value"])
        self.assertIn("not CPU utilization percent", c["detail"])

    def test_html_escapes_input(self):
        r = collector.demo_report()
        r["checks"][0]["label"] = '<script>alert("x")</script>'
        html = render_html(r)
        self.assertNotIn('<script>alert("x")</script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('name="robots" content="noindex,nofollow"', html)

    def test_html_is_self_contained(self):
        html = render_html(collector.demo_report())
        self.assertIn("<style>", html)
        self.assertNotIn('src="https://', html)
        self.assertIn("SIMULATED DEMO", html)
        self.assertIn("No real server", html)

    def test_invalid_port_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["--demo", "--port", "70000"]), 2)

    def test_sample_reports_generated(self):
        with TemporaryDirectory() as d:
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(["--demo", "--out-dir", d])
            self.assertEqual(code, 0)
            html = (Path(d) / "index.html").read_text(encoding="utf-8")
            content = (Path(d) / "report.json").read_text(encoding="utf-8")
            self.assertIn("SIMULATED DEMO", html)
            self.assertIn('"mode": "SIMULATED DEMO"', content)
            self.assertNotIn('"hostname"', content)
            self.assertNotIn('"ip_address"', content)


if __name__ == "__main__":
    unittest.main()