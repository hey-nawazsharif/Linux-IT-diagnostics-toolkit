# OpsPulse — Linux IT Diagnostics Toolkit

**Read-only, privacy-conscious Linux diagnostics in Python.** A compact professional IT Support learning project that collects useful machine-health signals and generates a self-contained HTML dashboard and machine-readable JSON report.

> **Project status:** Working v0.1 MVP. Not an enterprise monitoring agent or a substitute for an incident investigation. GitHub Actions runs against its own temporary Linux runner—not your personal iPhone/Mac/office server. Demo reports are **fictional** and explicitly labelled.

![Python stdlib](https://img.shields.io/badge/Python-3.11%2B-blue) ![License: MIT](https://img.shields.io/badge/License-MIT-informational) ![Platform: Linux](https://img.shields.io/badge/Live%20diagnostics-Linux-only-green)

## Features

| Diagnostic | What it measures | Default |
| --- | --- | --- |
| CPU pressure | 1-minute Linux load average per logical CPU | Yes, no network |
| Memory | Available vs total memory using `/proc/meminfo` | Yes, no network |
| Disk capacity | Usage/free space for the selected filesystem | Yes, no network |
| Uptime | Time since last boot from `/proc/uptime` | Yes, no network |
| Network interfaces | Up/total non-loopback interfaces (no IPs/MACs) | Yes, no network |
| DNS | Resolve a provided host, do not log returned IPs | Only with `--dns` |
| TCP reachability | Attempt TCP connection to a user-specified host and port | Only with `--tcp` |
| systemd services | Query services using `systemctl is-active` without shell | Only with `--service` |
| Backup restore | Explicitly marked **not verified** | Always |

**No sudo/root necessary**. No pip packages, paid APIs, signup, agent installation, telemetry collection or background daemon. The generated HTML includes its CSS, works offline, contains no analytics, and has `noindex,nofollow` metadata to reduce accidental indexing.

## Quick start on Linux

Requires Python 3.11+ on Linux:

```bash
python3 -m opspulse --out-dir reports
```

Creates:

- `reports/index.html` — self-contained report, open it in a browser.
- `reports/report.json` — structured data useful for ticket documentation.

Optional tests (explicitly opt in to external DNS/TCP and service state checks):

```bash
python3 -m opspulse --dns example.com --tcp example.com --port 443 --service ssh --out-dir reports
```

**Network notice:** The optional network probes contact the host you specify, and they can generate logs on that destination; use approved targets only. `--service ssh` checks the **local** machine. If systemd is unavailable, the check reports skipped. By default, no external network connections are attempted.

## Demo from any laptop or iPhone browser

You can preview a **fictional** report without Linux:

```bash
python3 -m opspulse --demo --out-dir docs
```

Open `docs/index.html`, or once deployed, view the GitHub Pages sample from `/docs` (repository Settings → Pages → Deploy from branch `main` → `/docs`). The sample is NOT evidence of measurements on a real user machine. All fake values are prominently labelled.

On iPhone, GitHub Actions can run Python unit tests on GitHub's Linux-hosted runner; a standard iPhone app cannot collect another Linux system's CPU, memory, disks, and services without an actual Linux endpoint. You do not need to install Python on the phone for this project.

## Exit status

- `0` — report generated, no critical checks (warnings can be present)
- `1` — a critical check occurred; report still generated
- `2` — invalid arguments, unsupported platform, or output failure

## Architecture

```text
python3 -m opspulse
    |
    +-- cli.py             Validate opt-in flags and output location
    +-- collector.py       /proc, /sys, shutil; optional DNS/TCP/systemctl
    +-- render.py          HTML escaping, self-contained CSS, safety labels
    +-- reports/index.html Openable offline in a browser
    +-- reports/report.json Structured ticket-friendly report
```

## Privacy and safety

- Read-only system observations. Does not run a vulnerability scan, alter files, kill processes or change service settings.
- Collects no usernames, IP addresses, MAC addresses, environment variables, authentication secrets or raw process command lines.
- The report contains explicitly requested DNS/TCP destination hostnames and service names. Do not use private customer names for public sample reports.
- **Never publish an unreviewed live report**: even non-secret operational data may be confidential. CI uploads only the simulated demo as an artifact. It runs the live diagnostic on its **temporary GitHub runner** without publishing its report.
- Memory threshold alerts are indicative. Linux load average is not CPU-use percentage; a disk-space report is not a SMART test.
- RAID is not backup; this tool does not assert that backup restoration succeeded.

## Test

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q opspulse tests
```

CI in `.github/workflows/ci.yml` repeats the tests and produces an example dashboard (no account secrets required).

## Roadmap

- [x] Read-only Linux system diagnostics
- [x] Responsive offline HTML and JSON reports
- [x] Unit tests, GitHub Actions example
- [ ] Optional alert threshold configuration and recurring health history
- [ ] Windows PowerShell adapter, separate from the Linux collector
- [ ] Dashboard UI for multiple **authorised** hosts and ticket history
- [ ] Production hardening, benchmarks, and broader distro validation

## License

MIT. Educational project, no warranties. Author: Nawaz Sharif.