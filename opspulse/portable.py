"""Local, read-only Windows/macOS/Linux point-in-time diagnostics.

Requires psutil installed locally (packaged with desktop builds). The module does
not read usernames, raw process details, IP/MAC addresses, environment variables,
or connect to any network by default. All tests are snapshots, not monitoring.
"""
from __future__ import annotations

import os
from pathlib import Path
import platform
import time
from typing import Any

from .collector import build_report, check, dns_check, tcp_check

def _psutil(module: Any | None = None) -> Any:
    if module is not None:
        return module
    try:
        import psutil
        return psutil
    except ImportError as exc:
        raise RuntimeError(
            "Cross-platform diagnostics require psutil. "
            "Run: python -m pip install -r requirements-desktop.txt"
        ) from exc


def _status(pct: float) -> str:
    return "critical" if pct >= 95 else "warn" if pct >= 85 else "pass"


def default_disk_path() -> Path:
    """Measure the primary filesystem without disclosing username paths."""
    return Path(Path.home().anchor or os.path.abspath(os.sep))


def collect_portable(
    *,
    psutil_module: Any | None = None,
    disk_path: Path | None = None,
    system_name: str | None = None,
    dns_hostname: str | None = None,
    tcp_hostname: str | None = None,
    tcp_port: int = 443,
    service_names: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Collect on the machine running this function. No remote access.

    Active DNS/TCP probes occur only when explicitly given a destination.
    Service checks remain Linux-specific and are labelled skipped elsewhere.
    """
    ps = _psutil(psutil_module)
    system = system_name or platform.system()
    if system not in {"Darwin", "Windows", "Linux"}:
        raise RuntimeError(f"Unsupported OS {system!r}; supported: Windows, macOS and Linux")
    if not 1 <= tcp_port <= 65535:
        raise ValueError("TCP port must be between 1 and 65535")
    if len(service_names) > 10:
        raise ValueError("Maximum 10 service names per run")

    entries: list[dict[str, str]] = []

    # CPU percent is a brief sampling interval; it is NOT Linux load average.
    try:
        cores = ps.cpu_count(logical=True)
        usage = float(ps.cpu_percent(interval=0.15))
        if not cores or not 0 <= usage <= 100:
            raise ValueError("Invalid CPU metrics")
        entries.append(check(
            "cpu_percent", "CPU utilisation (brief sample)", _status(usage),
            f"{usage:.1f}% sampled",
            f"Approx. 150 ms sampling interval across {cores} logical CPUs. "
            "A brief CPU sample does not show sustained load or root cause.",
        ))
    except (OSError, ValueError, AttributeError, TypeError):
        entries.append(check(
            "cpu_percent", "CPU utilisation (brief sample)", "skip", "Unavailable",
            "CPU sampling is unsupported in this environment."
        ))

    try:
        mem = ps.virtual_memory()
        total, available = int(mem.total), int(mem.available)
        if total <= 0 or not 0 <= available <= total:
            raise ValueError("Invalid RAM counters")
        pct = 100 * (total - available) / total
        entries.append(check(
            "ram_portable", "Available memory", _status(pct), f"{pct:.1f}% in use",
            f"{available / (1024 ** 3):.1f} GiB available of {total / (1024 ** 3):.1f} GiB. "
            "Based on OS available-memory estimates, not individual processes.",
        ))
    except (OSError, ValueError, AttributeError, TypeError):
        entries.append(check("ram_portable", "Available memory", "skip", "Unavailable",
                             "OS memory counters could not be read."))

    try:
        swap = ps.swap_memory()
        total, used = int(swap.total), int(swap.used)
        if total < 0 or used < 0:
            raise ValueError("Invalid swap counters")
        if total == 0:
            value, detail = "Not configured", (
                "No swap/page-file capacity reported. This is not automatically an error."
            )
        else:
            value, detail = f"{min(100, 100 * used / total):.1f}% allocated", (
                f"{used / (1024 ** 3):.1f} GiB allocated of {total / (1024 ** 3):.1f} GiB. "
                "Swap allocation alone does not prove active paging or memory pressure."
            )
        entries.append(check("swap_portable", "Swap / page-file occupancy", "info", value, detail))
    except (OSError, ValueError, AttributeError, TypeError):
        entries.append(check("swap_portable", "Swap / page-file occupancy", "skip", "Unavailable",
                             "Swap/page-file counters could not be read."))

    target = Path(disk_path) if disk_path is not None else default_disk_path()
    try:
        disk = ps.disk_usage(str(target))
        total, used, free = int(disk.total), int(disk.used), int(disk.free)
        if total <= 0 or min(used, free) < 0:
            raise ValueError("Invalid disk usage")
        pct = 100 * used / total
        entries.append(check(
            "disk_portable", "System filesystem capacity", _status(pct), f"{pct:.1f}% used",
            f"{free / (1024 ** 3):.1f} GiB free of {total / (1024 ** 3):.1f} GiB. "
            "Capacity only; no SMART health, physical-drive inventory or file scanning.",
            category="storage",
        ))
    except (OSError, ValueError, AttributeError, TypeError):
        entries.append(check("disk_portable", "System filesystem capacity", "skip", "Unavailable",
                             "Cannot read selected filesystem capacity.", category="storage"))

    # Windows does not use inode semantics; macOS/APFS inode counters also do not
    # provide the Linux-style finite inode exhaustion alert. Do not invent one.
    entries.append(check(
        "inodes", "Linux inode availability", "skip", "Not applicable",
        "Inode exhaustion check applies to the Linux collector; not a Windows/macOS health failure.",
        category="storage",
    ))

    try:
        seconds = max(0.0, float(time.time()) - float(ps.boot_time()))
        if seconds > 100 * 365 * 86400:
            raise ValueError("Invalid boot timestamp")
        days, hours = divmod(int(seconds // 3600), 24)
        entries.append(check(
            "uptime", "Time since startup", "info", f"{days} days, {hours} hours",
            "Estimated from OS boot time; long uptime alone does not establish system health.",
        ))
    except (OSError, ValueError, AttributeError, TypeError):
        entries.append(check("uptime", "Time since startup", "skip", "Unavailable",
                             "Cannot determine last system boot time."))

    try:
        stats = ps.net_if_stats()
        if not isinstance(stats, dict):
            raise ValueError("Unexpected interface map")
        count = len(stats)
        active = sum(bool(s.isup) for s in stats.values())
        status = "warn" if count > 0 and active == 0 else "info"
        entries.append(check(
            "interfaces", "Network interface states", status,
            f"{active} up / {count} interfaces",
            "Includes virtual and loopback interfaces. IP/MAC addresses, interface names, "
            "traffic and remote reachability are not collected. An up interface is not a connection test.",
            category="network",
        ))
    except (OSError, ValueError, AttributeError, TypeError):
        entries.append(check("interfaces", "Network interface states", "skip", "Unavailable",
                             "Network interface status cannot be read.", category="network"))

    if dns_hostname:
        entries.append(dns_check(dns_hostname))
    if tcp_hostname:
        entries.append(tcp_check(tcp_hostname, tcp_port))

    for name in service_names:
        # The Linux CLI uses its existing systemctl implementation.
        entries.append(check(
            "service", "Requested service check", "skip", "Not supported here",
            "Platform service checks require a platform-specific implementation. "
            "This app does not execute arbitrary commands or remote checks.",
            category="service",
        ))

    entries.append(check(
        "backup", "Backup restore verification", "skip", "Not tested",
        "Only an authorised, isolated restore test can establish recoverability.",
        category="service",
    ))
    report = build_report(entries)
    report["mode"] = "LIVE LOCAL " + ("MACOS" if system == "Darwin" else system.upper())
    report["tool"] = "OpsPulse — Local System Diagnostics"
    report["network_probes"] = (
        "Optional: explicitly requested DNS/TCP destinations only."
        if dns_hostname or tcp_hostname else
        "No external DNS/TCP probes were requested or performed."
    )
    return report
