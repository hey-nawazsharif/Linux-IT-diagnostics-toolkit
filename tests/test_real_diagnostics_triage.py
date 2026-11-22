"""Read-only inode/swap and actionable triage report regressions."""
import contextlib
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from opspulse import cli, collector
from opspulse.render import render_html
from opspulse.triage import action_plan


class InodeTests(unittest.TestCase):
    def fake(self, total, available):
        return lambda path: SimpleNamespace(f_files=total, f_favail=available)

    def test_inodes_pass(self):
        item = collector.inode_check(Path("/"), stat=self.fake(1000, 200))
        self.assertEqual(item["status"], "pass")
        self.assertEqual(item["value"], "80.0% used")
        self.assertEqual(item["category"], "storage")

    def test_inodes_warn(self):
        item = collector.inode_check(Path("/"), stat=self.fake(1000, 100))
        self.assertEqual(item["status"], "warn")
        self.assertIn("90.0%", item["value"])

    def test_inodes_critical(self):
        item = collector.inode_check(Path("/"), stat=self.fake(1000, 40))
        self.assertEqual(item["status"], "critical")

    def test_inodes_zero_total_not_reported(self):
        item = collector.inode_check(Path("/"), stat=self.fake(0, 0))
        self.assertEqual(item["status"], "skip")
        self.assertIn("does not expose", item["detail"])

    def test_invalid_or_unavailable_inode_data(self):
        self.assertEqual(collector.inode_check(Path("/"), stat=self.fake(100, 200))["status"], "skip")
        def fail(path):
            raise OSError("no filesystem")
        self.assertEqual(collector.inode_check(Path("/"), stat=fail)["status"], "skip")


class SwapTests(unittest.TestCase):
    def mem(self, directory, swap_total, swap_free):
        p = Path(directory) / "meminfo"
        p.write_text(f"SwapTotal: {swap_total} kB\nSwapFree: {swap_free} kB\n", encoding="ascii")
        return p

    def test_swap_occupancy_is_informational_not_automatic_fault(self):
        with TemporaryDirectory() as d:
            result = collector.swap_check(self.mem(d, 100000, 10000))
        self.assertEqual(result["status"], "info")
        self.assertIn("90.0%", result["value"])
        self.assertIn("does not prove", result["detail"])

    def test_absent_swap_is_not_automatically_bad(self):
        with TemporaryDirectory() as d:
            result = collector.swap_check(self.mem(d, 0, 0))
        self.assertEqual(result["status"], "info")
        self.assertEqual(result["value"], "Not configured")

    def test_bad_swap_values_skipped(self):
        with TemporaryDirectory() as d:
            result = collector.swap_check(self.mem(d, 100, 200))
        self.assertEqual(result["status"], "skip")


class TriageTests(unittest.TestCase):
    def test_action_plan_priority_order_and_safe_backup_verification(self):
        entries = [
            collector.check("backup", "Backup restore verification", "skip", "Not tested"),
            collector.check("disk", "Root filesystem", "warn", "90% used"),
            collector.check("inodes", "Inodes", "critical", "99% used"),
            collector.check("swap", "Swap", "info", "90% allocated"),
        ]
        plan = action_plan(entries)
        self.assertEqual([x["priority"] for x in plan], ["critical", "warn", "verification"])
        self.assertIn("df -i", plan[0]["next_steps"][0])
        self.assertIn("restore", plan[-1]["next_steps"][0].lower())
        self.assertNotIn("swap", [x["check_key"] for x in plan])

    def test_unsupported_check_is_not_a_false_failure(self):
        plan = action_plan([collector.check("inodes", "Inodes", "skip", "Not supported")])
        self.assertEqual(plan[0]["priority"], "verification")
        self.assertIn("unverified", plan[0]["next_steps"][0].lower())

    def test_fictional_and_real_reports_keep_triage_structured(self):
        demo = collector.demo_report()
        self.assertEqual(demo["schema_version"], "1.1")
        self.assertEqual([a["check_key"] for a in demo["action_plan"]], ["disk", "backup"])
        sample = collector.build_report([
            collector.check("ram", "Memory", "critical", "98%"),
            collector.check("inodes", "Inodes", "warn", "90%"),
            collector.check("backup", "Restore", "skip", "Not tested")
        ])
        self.assertEqual([a["priority"] for a in sample["action_plan"]], ["critical", "warn", "verification"])

    def test_html_report_escapes_untrusted_data_and_has_followups(self):
        report = collector.build_report([
            collector.check("disk", "<img src=x onerror=alert(1)>", "critical", "<script>x()</script>"),
            collector.check("backup", "Restore", "skip", "Not tested")
        ])
        html = render_html(report)
        self.assertIn('id="action-plan"', html)
        self.assertIn("Recommended troubleshooting next steps", html)
        self.assertIn("df -h", html)
        self.assertIn("&lt;script&gt;x()&lt;/script&gt;", html)
        self.assertNotIn("<script>x()</script>", html)
        self.assertIn("Not verified", html)
        self.assertNotIn("auto-fix", html)

    def test_report_disclaims_smart_and_backup_verification(self):
        text = render_html(collector.demo_report())
        self.assertIn("not a SMART drive-health test", text)
        self.assertIn("restore test", text)
        self.assertIn("ordered", text.lower())


class OutputSafetyTests(unittest.TestCase):
    def test_cli_refuses_overwriting_interactive_docs(self):
        with TemporaryDirectory() as d:
            docs = Path(d) / "docs"
            docs.mkdir()
            page = docs / "index.html"
            page.write_text('<script id="seed-report" type="application/json">{}</script>', encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()) as output:
                result = cli.main(["--demo", "--out-dir", str(docs)])
            self.assertEqual(result, 2)
            self.assertIn("interactive OpsPulse dashboard", output.getvalue())
            self.assertIn('id="seed-report"', page.read_text(encoding="utf-8"))
            self.assertFalse((docs / "report.json").exists())


if __name__ == "__main__":
    unittest.main()
