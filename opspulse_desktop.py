"""OpsPulse desktop launcher for Windows, macOS and Linux.

--self-test exercises the same packaged local collector without opening Tk.
Used for platform-specific binary smoke checks in CI; no network probes.
"""
from __future__ import annotations
import sys

from opspulse.desktop import main, collect_local

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        report = collect_local()
        assert report["mode"].startswith("LIVE LOCAL"), "Expected actual local diagnostics"
        assert report["summary"]["skip"] >= 1, "Backup restore must be unverified"
        assert len(report["checks"]) >= 7, "Missing key system metrics"
        print("PASS: packaged OpsPulse local collector; no network probes")
        raise SystemExit(0)
    raise SystemExit(main())
