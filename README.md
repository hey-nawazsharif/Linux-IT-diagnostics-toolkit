# OpsPulse — Linux IT Diagnostics Toolkit

**Read-only, privacy-conscious Linux diagnostics in Python.** A compact professional IT Support learning project that collects useful machine-health signals and generates a self-contained HTML dashboard and machine-readable JSON report.

> **Project status:** Working v0.2 interactive MVP. Not an enterprise monitoring agent or a substitute for an incident investigation. GitHub Actions runs against its own temporary Linux runner—not your personal iPhone/Mac/office server. Demo reports are **fictional** and explicitly labelled.

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

## Interactive demo from any laptop or iPhone browser

**Public interactive demonstration:** https://hey-nawazsharif.github.io/Linux-IT-diagnostics-toolkit/

The GitHub Pages app (`docs/index.html` + `docs/app.js`) now provides:

- **Run simulated diagnostics** using four fictional scenarios (baseline, healthy, warnings, critical).
- Filter by health status, search checks and open relevant troubleshooting guidance.
- Download the current report as JSON, or print/save the dashboard.
- **Open an OpsPulse JSON report locally in the browser** to inspect a real machine's output without uploading it. Uploaded files are treated as *unverified claims*, and all text is rendered safely. File size limited to 1 MB.
- Completely browser-side functionality: **no scans of the visitor's device, no remote API calls, analytics, tracking, accounts or paid hosting requirements**. Fictional demo measurements are labelled `SIMULATED DEMO`.

To produce an actual point-in-time report, run the CLI on an **authorised Linux machine** (Python 3.11+):

```bash
python3 -m opspulse --out-dir reports
```

Then use **Open a local JSON report** on the website and select `reports/report.json`. Review its contents and your organisation's policy before sharing any report. The browser does **not** remotely read CPU or network metrics; a static GitHub Pages site has no permission or backend to do so.

The collector can also generate a separate, fully offline fictional HTML/JSON example:

```bash
python3 -m opspulse --demo --out-dir reports/demo
```

Open `reports/demo/index.html` locally. Do **not** run the CLI demo with `--out-dir docs` in your source checkout, as that overwrites the interactive site's `docs/index.html`.

On iPhone, GitHub Actions can run unit tests using a temporary GitHub-hosted Linux runner; it **does not measure your iPhone or any office machine**. You do not need Python installed on the phone for the browser dashboard.

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

CI in `.github/workflows/ci.yml` repeats Python and Node tests, validates the interactive browser dashboard, and produces a separate offline demo report (no account secrets required).

## Roadmap

- [x] Read-only Linux system diagnostics
- [x] Responsive offline HTML and JSON reports
- [x] Unit tests, GitHub Actions example
- [x] Interactive GitHub Pages simulated scenarios, report filtering and local JSON viewer
- [ ] Optional alert threshold configuration and recurring health history
- [ ] Windows PowerShell adapter, separate from the Linux collector
- [ ] Dashboard UI for multiple **authorised** hosts and ticket history
- [ ] Production hardening, benchmarks, and broader distro validation

## License

MIT. Educational project, no warranties. Author: Nawaz Sharif.