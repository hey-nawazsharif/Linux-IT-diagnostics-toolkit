"""Console entry point: safe defaults, explicit active probes, two output formats."""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import sys

from .collector import collect, demo_report
from .portable import collect_portable
from .report_io import write_report

HOST_PATTERN = re.compile(r"^(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?$")


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python3 -m opspulse",
        description="Local, read-only Windows/macOS/Linux diagnostics and HTML/JSON reports. Default: no outbound network probes.",
    )
    p.add_argument("--demo", action="store_true", help="Create a clearly labelled fictional report (works on any OS)")
    p.add_argument("--out-dir", type=Path, default=Path("reports"), help="Output directory, default: ./reports")
    p.add_argument("--disk-path", type=Path, default=None, help="Filesystem to inspect (default OS system drive)")
    p.add_argument("--dns", metavar="HOST", help="Opt in to DNS lookup of this host")
    p.add_argument("--tcp", metavar="HOST", help="Opt in to outbound TCP port test of this host")
    p.add_argument("--port", type=int, default=443, help="TCP port for --tcp, default 443")
    p.add_argument("--service", action="append", default=[], metavar="NAME", help="Optional Linux systemd service; unsupported on Windows/macOS")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    if not 1 <= args.port <= 65535:
        print("Error: TCP port must be 1..65535", file=sys.stderr)
        return 2
    for host in (args.dns, args.tcp):
        if host and not HOST_PATTERN.fullmatch(host):
            print("Error: invalid hostname (use a DNS hostname or simple IPv4 string)", file=sys.stderr)
            return 2
    try:
        # Validate names in both live and demo modes to catch misspelt/suspicious args.
        if len(args.service) > 10 or any(not re.fullmatch(r"[A-Za-z0-9@_.-]{1,100}", s) for s in args.service):
            raise ValueError("Max 10 service names; only letters, digits, @ . _ - are allowed")
        if args.demo:
            report = demo_report()
        elif sys.platform == "linux":
            report = collect(
                disk_path=args.disk_path or Path("/"),
                dns_hostname=args.dns, tcp_hostname=args.tcp,
                tcp_port=args.port, service_names=tuple(args.service))
        else:
            report = collect_portable(
                disk_path=args.disk_path,
                dns_hostname=args.dns, tcp_hostname=args.tcp,
                tcp_port=args.port, service_names=tuple(args.service))
        json_file, html_file = write_report(report, args.out_dir)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    s = report["summary"]
    print(f"OpsPulse | {report['mode']} | {s['pass']} healthy, {s['warn']} attention, {s['critical']} critical, {s['skip']} unverified")
    print(f"JSON: {json_file}\nHTML: {html_file}")
    return 1 if s["critical"] > 0 else 0