"""Safe, read-only IT support follow-up guidance for point-in-time Linux reports.

Guidance is intentionally independent of thresholds and individual host identity.
A warning is not a diagnosis; verification items are not passed tests.
"""
from __future__ import annotations

from typing import Any

GUIDANCE: dict[str, tuple[str, str]] = {
    "cpu": (
        "Compare load average with logical CPUs and inspect process, I/O-wait and scheduler pressure. High load is not equivalent to CPU utilisation.",
        "Check workload changes and incident timing before restarting or stopping anything."
    ),
    "ram": (
        "Review MemAvailable, swap activity and process memory with free -h and authorised observability tools.",
        "Confirm whether memory pressure persists before changing limits, services or hardware."
    ),
    "disk": (
        "Run df -h on the affected filesystem and review growth, log retention and application storage policy.",
        "Do not delete unknown files or logs without checking owners, backups and retention requirements."
    ),
    "inodes": (
        "Run df -i for the filesystem; free disk space alone does not rule out inode exhaustion.",
        "Identify approved workloads producing many small files; review retention before deleting files."
    ),
    "interfaces": (
        "Check physical or virtual link state, approved switch ports and interface configuration using ip -br link.",
        "An interface being up does not prove DNS, routing or application availability."
    ),
    "dns": (
        "Inspect authorised resolver configuration, route and domain-specific resolution, such as resolvectl status.",
        "DNS success or failure alone does not establish end-to-end web service health."
    ),
    "tcp": (
        "Verify the intended destination and port, firewall rules and service listeners using approved diagnostics.",
        "TCP connectivity does not prove TLS security or a successful application request."
    ),
    "service": (
        "Confirm the service is expected to be active; review its systemctl status and relevant logs locally.",
        "Avoid publishing raw logs or restarting production services without an approved change procedure."
    ),
    "backup": (
        "Perform a separate authorised restore test to isolated storage; verify restored data and record evidence.",
        "A backup job's last success and RAID redundancy do not prove recoverability."
    )
}


def action_plan(checks: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Provide ordered human follow-ups, not automated repairs or diagnoses.

    'skip' entries are labelled verification, not health failures.
    No host identifiers, IP addresses, processes, commands or secrets are
    retrieved by this function.
    """
    priorities = {"critical": 0, "warn": 1, "skip": 2}
    follow_ups: list[dict[str, Any]] = []
    for item in checks:
        status = item.get("status", "")
        if status not in priorities:
            continue
        key = item.get("key", "")
        steps = GUIDANCE.get(key, (
            "Review the check's scope, its data source and the documented requirements for this service.",
            "Gather authorised logs or measurements and verify the issue before making changes."
        ))
        if status == "skip" and key != "backup":
            steps = (
                "This check is unverified or unsupported in the current environment; confirm whether it applies.",
                "Re-run on a compatible Linux host with appropriate permissions, or use a trusted alternative."
            )
        follow_ups.append({
            "check_key": key,
            "label": item.get("label", "Unnamed check"),
            "priority": "verification" if status == "skip" else status,
            "observed": item.get("value", "Unknown"),
            "next_steps": list(steps),
        })
    return sorted(follow_ups, key=lambda entry: priorities["skip" if entry["priority"] == "verification" else entry["priority"]])
