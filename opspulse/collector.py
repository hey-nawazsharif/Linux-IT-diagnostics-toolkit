"""Read-only Linux collector: no root, no secret collection, no network by default."""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
from typing import Any

from .triage import action_plan

MAX_SERVICES = 10
SERVICE_PATTERN = re.compile(r"^[a-zA-Z0-9@_.-]{1,100}$")


def check(key: str, label: str, status: str, value: str, detail: str = "", *, category: str = "system") -> dict[str, str]:
    if status not in {"pass", "warn", "critical", "info", "skip"}:
        raise ValueError("Unknown status")
    return {"key": key, "label": label, "status": status, "value": value, "detail": detail, "category": category}


def read_meminfo(path: Path = Path("/proc/meminfo")) -> dict[str, int]:
    """Linux meminfo values are in KiB. Do not treat cached/buffers as unavailable."""
    data: dict[str, int] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        match = re.match(r"\s*(\d+)\s*kB", raw)
        if match:
            data[key] = int(match.group(1))
    return data


def memory_check(path: Path = Path("/proc/meminfo")) -> dict[str, str]:
    try:
        data = read_meminfo(path)
        total, available = data["MemTotal"], data["MemAvailable"]
        if total <= 0 or not 0 <= available <= total:
            raise ValueError("Invalid meminfo values")
        used_pct = 100 * (total - available) / total
        gib_total = total / (1024**2)
        gib_avail = available / (1024**2)
        status = "critical" if used_pct >= 95 else "warn" if used_pct >= 85 else "pass"
        return check("ram", "Memory availability", status, f"{used_pct:.1f}% in use", f"{gib_avail:.1f} GiB estimated available of {gib_total:.1f} GiB. Based on Linux MemAvailable; not a process-level measurement.")
    except (OSError, KeyError, ValueError) as exc:
        return check("ram", "Memory availability", "skip", "Unavailable", f"Cannot read Linux memory counters: {type(exc).__name__}.")


def cpu_check() -> dict[str, str]:
    try:
        cores = os.cpu_count()
        if not cores or cores <= 0:
            raise ValueError("No core count")
        load1, _, _ = os.getloadavg()
        ratio = load1 / cores
        status = "critical" if ratio >= 2 else "warn" if ratio >= 1 else "pass"
        return check("cpu", "CPU load pressure", status, f"{load1:.2f} load / {cores} logical CPUs", f"1-minute Linux load average per logical CPU: {ratio:.2f}. Includes runnable and uninterruptible tasks; not CPU utilization percent.")
    except (OSError, ValueError):
        return check("cpu", "CPU load pressure", "skip", "Unavailable", "Could not obtain Linux load average.")


def disk_check(path: Path, *, label: str | None = None) -> dict[str, str]:
    location = str(path)
    safe_label = label or f"Disk at {location}"
    try:
        usage = shutil.disk_usage(path)
        if usage.total == 0:
            raise ValueError("Invalid disk capacity")
        pct = 100 * usage.used / usage.total
        status = "critical" if pct >= 95 else "warn" if pct >= 85 else "pass"
        return check("disk", safe_label, status, f"{pct:.1f}% used", f"{usage.free/(1024**3):.1f} GiB free / {usage.total/(1024**3):.1f} GiB total. This checks the filesystem, not SSD wear or SMART health.", category="storage")
    except (OSError, ValueError):
        return check("disk", safe_label, "skip", "Unavailable", "Cannot read disk capacity for the selected path.", category="storage")


def inode_check(path: Path, *, stat=None) -> dict[str, str]:
    """Read available filesystem inode counts without listing user files.

    os.statvfs does not exist on Windows. Resolve it only at call time so
    importing the package works on Windows even though inodes are Linux-only.
    """
    stat_fn = stat if stat is not None else getattr(os, "statvfs", None)
    if stat_fn is None:
        return check("inodes", "Filesystem inode availability", "skip", "Not supported",
                     "This platform does not provide POSIX inode counters.",
                     category="storage")
    try:
        fs = stat_fn(path)
        total = int(fs.f_files)
        available = int(fs.f_favail)
        if total <= 0:
            return check("inodes", "Filesystem inode availability", "skip", "Not reported",
                         "This filesystem does not expose an inode total. This is not evidence of a fault.",
                         category="storage")
        if not 0 <= available <= total:
            raise ValueError("Invalid inode counters")
        used_pct = 100 * (total - available) / total
        status = "critical" if used_pct >= 95 else "warn" if used_pct >= 85 else "pass"
        return check("inodes", "Filesystem inode availability", status, f"{used_pct:.1f}% used",
                     f"{available:,} inodes available of {total:,}. Read-only filesystem counters; "
                     "inode availability differs from free disk bytes and does not measure SSD wear.",
                     category="storage")
    except (OSError, ValueError, TypeError, AttributeError):
        return check("inodes", "Filesystem inode availability", "skip", "Unavailable",
                     "Unable to read inode counters for the selected filesystem.",
                     category="storage")


def swap_check(path: Path = Path("/proc/meminfo")) -> dict[str, str]:
    """Show swap occupancy as context, not automatic proof of memory pressure."""
    try:
        data = read_meminfo(path)
        total, free = data["SwapTotal"], data["SwapFree"]
        if total < 0 or not 0 <= free <= total:
            raise ValueError("Invalid swap counters")
        if total == 0:
            return check("swap", "Swap occupancy", "info", "Not configured",
                         "No swap space reported. That is not automatically a fault; assess the workload and memory policy.")
        pct = 100 * (total - free) / total
        return check("swap", "Swap occupancy", "info", f"{pct:.1f}% allocated",
                     f"{(total - free)/(1024**2):.1f} GiB allocated of {total/(1024**2):.1f} GiB. "
                     "Swap allocation alone does not prove active swapping or memory pressure.")
    except (OSError, ValueError, KeyError):
        return check("swap", "Swap occupancy", "skip", "Unavailable",
                     "Swap counters could not be read from Linux meminfo.")


def uptime_check(path: Path = Path("/proc/uptime")) -> dict[str, str]:
    try:
        seconds = float(path.read_text(encoding="ascii").split()[0])
        if seconds < 0:
            raise ValueError("Bad uptime")
        days, hours = divmod(int(seconds // 3600), 24)
        return check("uptime", "System uptime", "info", f"{days} days, {hours} hours", "Time since boot; high uptime alone does not prove good health.")
    except (OSError, ValueError, IndexError):
        return check("uptime", "System uptime", "skip", "Unavailable", "Linux /proc uptime not available.")


def interface_check(path: Path = Path("/sys/class/net")) -> dict[str, str]:
    try:
        interfaces = sorted(p for p in path.iterdir() if p.name != "lo")
        if not interfaces:
            return check("interfaces", "Network interfaces", "info", "None detected", "No non-loopback interface names were found.", category="network")
        active = 0
        for interface in interfaces:
            try:
                active += (interface / "operstate").read_text(encoding="ascii").strip() == "up"
            except OSError:
                continue
        return check("interfaces", "Network interfaces", "pass" if active else "warn", f"{active} up / {len(interfaces)} non-loopback", "Only local operational state is read. IPs, MAC addresses and interface names are deliberately omitted from public reports.", category="network")
    except OSError:
        return check("interfaces", "Network interfaces", "skip", "Unavailable", "Network sysfs counters unavailable.", category="network")


def dns_check(hostname: str, *, resolver=socket.getaddrinfo) -> dict[str, str]:
    """Explicit opt-in; never write the resolved addresses to the report."""
    try:
        resolver(hostname, 443, type=socket.SOCK_STREAM)
        return check("dns", "DNS resolution", "pass", "Resolved", f"DNS resolution for {hostname} succeeded; HTTP connectivity was not tested.", category="network")
    except (socket.gaierror, OSError, ValueError):
        return check("dns", "DNS resolution", "warn", "Failed", f"DNS resolution failed for {hostname}; verify network/DNS configuration.", category="network")


def tcp_check(hostname: str, port: int = 443, timeout: float = 3.0, *, connector=socket.create_connection) -> dict[str, str]:
    """Explicit opt-in; verifies TCP port reachability, not application security."""
    try:
        with connector((hostname, port), timeout=timeout):
            pass
        return check("tcp", "TCP connectivity", "pass", "Connected", f"TCP connection to {hostname}:{port} established; TLS/app response not validated.", category="network")
    except (OSError, ValueError):
        return check("tcp", "TCP connectivity", "warn", "Failed", f"TCP connection to {hostname}:{port} failed within timeout.", category="network")


def service_check(service: str, *, runner=subprocess.run) -> dict[str, str]:
    if not SERVICE_PATTERN.fullmatch(service):
        raise ValueError("Invalid service name: only letters, digits, @ . _ - are allowed")
    try:
        p = runner(["systemctl", "is-active", "--", service], capture_output=True, text=True, timeout=5, check=False)
        state = p.stdout.strip().lower()
        if state == "active":
            return check("service", f"Service {service}", "pass", "Active", "systemctl reports an active service; deeper application health is not measured.", category="service")
        if state in {"inactive", "failed", "activating", "deactivating"}:
            return check("service", f"Service {service}", "warn", state.capitalize(), "Service was explicitly requested for checking; determine whether it should be running.", category="service")
        return check("service", f"Service {service}", "skip", "Unknown", "systemd service state could not be interpreted; systemd may be unavailable.", category="service")
    except (OSError, subprocess.TimeoutExpired):
        return check("service", f"Service {service}", "skip", "Unavailable", "systemctl is not available or the command timed out.", category="service")


def demo_report() -> dict[str, Any]:
    """Clearly fictional sample for mobile viewing and GitHub Pages, never real machine data."""
    entries = [
        check("cpu", "CPU load pressure", "pass", "0.42 load / 8 logical CPUs", "Example 1-minute load. No real computer was inspected."),
        check("ram", "Memory availability", "pass", "44.0% in use", "Simulated 16.0 GiB total RAM; values are illustrations."),
        check("disk", "Root filesystem", "warn", "87.0% used", "Simulated disk space warning. An operator could review old logs or adjust capacity.", category="storage"),
        check("uptime", "System uptime", "info", "5 days, 9 hours", "Illustrative uptime."),
        check("interfaces", "Network interfaces", "pass", "1 up / 2 non-loopback", "Interface names, IPs and MACs are intentionally hidden.", category="network"),
        check("dns", "DNS resolution", "pass", "Resolved", "Simulated external check to example.com, not executed.", category="network"),
        check("service", "Service ssh", "pass", "Active", "Simulated service status, not tested on a live server.", category="service"),
        check("backup", "Backup restore verification", "skip", "Not tested", "A live restore needs separate manual evidence; this tool does not claim to validate backups.", category="service"),
    ]
    return build_report(entries, demo=True)


def build_report(entries: list[dict[str, str]], *, demo: bool = False) -> dict[str, Any]:
    counts = {status: sum(c["status"] == status for c in entries) for status in ("pass", "warn", "critical", "info", "skip")}
    return {
        "schema_version": "1.1",
        "tool": "OpsPulse — Linux IT Diagnostics Toolkit",
        "mode": "SIMULATED DEMO" if demo else "LIVE LOCAL LINUX",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "privacy": "No passwords, environment variables, IP addresses, MAC addresses or username/hostname inventory are collected.",
        "network_probes": "Opt-in only. Local mode has no external probes by default." if not demo else "SIMULATED — no real network connections were made.",
        "checks": entries,
        "summary": counts,
        "action_plan": action_plan(entries),
    }


def collect(*, disk_path: Path = Path("/"), dns_hostname: str | None = None,
            tcp_hostname: str | None = None, tcp_port: int = 443,
            service_names: tuple[str, ...] = ()) -> dict[str, Any]:
    if sys.platform != "linux":
        raise RuntimeError("Live diagnostics are supported on Linux only. Use --demo on macOS/iPhone or GitHub Pages.")
    if len(service_names) > MAX_SERVICES:
        raise ValueError("Maximum 10 services per run")
    for service in service_names:
        if not SERVICE_PATTERN.fullmatch(service):
            raise ValueError("Invalid service name: use letters, digits, @ . _ - only")
    entries = [
        cpu_check(),
        memory_check(),
        swap_check(),
        disk_check(disk_path, label="Selected filesystem"),
        inode_check(disk_path),
        uptime_check(),
        interface_check(),
    ]
    if dns_hostname:
        entries.append(dns_check(dns_hostname))
    if tcp_hostname:
        entries.append(tcp_check(tcp_hostname, tcp_port))
    for service in service_names:
        entries.append(service_check(service))
    entries.append(check("backup", "Backup restore verification", "skip", "Not tested", "Read-only diagnostics cannot prove that backup restoration works. Perform and document a separate restore test.", category="service"))
    return build_report(entries)