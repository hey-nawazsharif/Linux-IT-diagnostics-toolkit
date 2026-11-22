# OpsPulse — Local IT Diagnostics (Windows · macOS · Linux)

**Read-only, privacy-conscious desktop and CLI diagnostics in Python.** A practical IT Support project with a local one-click desktop UI, real point-in-time CPU/memory/disk/network-state checks, optional local HTML/JSON reports, and a separate simulated web demonstration.

> **Project status:** v0.6 cross-platform **unsigned developer beta**. Windows/macOS/Linux builds and real local host checks are tested on temporary GitHub Actions runners, not on your personal computer. Requires further user-device GUI tests, security review, signing/notarisation and OS-version coverage. The web demo is **fictional** and explicitly labelled; the downloaded desktop app performs real local checks only after user interaction.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue) ![License: MIT](https://img.shields.io/badge/License-MIT-informational) ![Platform: Windows macOS Linux](https://img.shields.io/badge/Desktop-Windows%20%7C%20macOS%20%7C%20Linux-green)

## Features

| Diagnostic | What it measures | Default |
| --- | --- | --- |
| CPU pressure | 1-minute Linux load average per logical CPU | Yes, no network |
| Memory | Available vs total memory using `/proc/meminfo` | Yes, no network |
| Disk capacity | Usage/free space for the selected filesystem | Yes, no network |
| Filesystem inodes | Available inode count via read-only `os.statvfs` | Yes, no network; skipped if unsupported |
| Swap occupancy | Used/free swap from `/proc/meminfo`; informational, not proof of pressure | Yes, no network |
| Uptime | Time since last boot from `/proc/uptime` | Yes, no network |
| Network interfaces | Up/total non-loopback interfaces (no IPs/MACs) | Yes, no network |
| DNS | Resolve a provided host, do not log returned IPs | Only with `--dns` |
| TCP reachability | Attempt TCP connection to a user-specified host and port | Only with `--tcp` |
| systemd services | Query services using `systemctl is-active` without shell | Only with `--service` |
| Backup restore | Explicitly marked **not verified** | Always |
| Prioritised action plan | Suggested safe next checks for critical, warning and unverified items | Automatic in HTML and JSON; does not repair anything |

**No root/admin necessary.** No paid APIs, signup, telemetry collection or background daemon. The Linux CLI uses Python standard library only; Windows/macOS CLI and source desktop UI use the open-source `psutil` dependency. Packaged desktop builds bundle their runtime. The generated HTML works offline with no external scripts or analytics.

## Desktop beta — Windows, macOS and Linux

**Public prerelease downloads (only after all four build jobs pass):**
[GitHub Releases](https://github.com/hey-nawazsharif/Linux-IT-diagnostics-toolkit/releases)

Read [DESKTOP_BETA.md](DESKTOP_BETA.md) for platform-specific Windows x64, Mac Apple Silicon (including M2), Mac Intel and Linux x64 packages, SHA-256 verification, installation cautions, and the difference between actual desktop scans and the browser demo.

The desktop app lets the user explicitly click **Run health check**, inspect local CPU/RAM/disk/swap/uptime/network-state values, and optionally choose **Save HTML + JSON**. It does not scan remote systems, auto-upload data, repair problems or execute network probes by default. Windows/macOS Linux-specific service/inode checks are transparently marked not applicable. These are **unsigned developer-preview builds**: OS warnings and compatibility issues are possible.

Run from source on your own computer using Python 3.11+:

```bash
git clone https://github.com/hey-nawazsharif/Linux-IT-diagnostics-toolkit.git
cd Linux-IT-diagnostics-toolkit
python -m pip install -r requirements-desktop.txt
python -m opspulse.desktop
```

If `python` is unavailable on your Linux/macOS terminal, try `python3`. Tk may require installing the operating system's Python Tk GUI support. Optional CLI on all three supported OSes: `python -m opspulse --out-dir reports`.

## What each platform measures

| OS | CPU | Memory | Disk | Network | Inodes & services |
| --- | --- | --- | --- | --- | --- |
| Windows | Short CPU utilisation sample | OS available RAM | System-drive capacity, pagefile (info) | Local interface up/down summary | Linux-only checks are skipped |
| macOS | Short CPU utilisation sample | OS available RAM | System-filesystem capacity, swap (info) | Local interface up/down summary | Linux-only checks are skipped |
| Linux | Load average / logical CPU | /proc/meminfo | Filesystem capacity + inode availability, swap (info) | Local interface operational state | Optional systemd checks |

Values are local snapshots, not a medical-style “health score”, vulnerability audit, remote scan or forecast. Windows/macOS CPU percent is not directly comparable to Linux load average. Optional CLI `--dns` and `--tcp` network probes require a user-supplied approved destination; none run by default.

## Quick start on Linux

Requires Python 3.11+ on a Linux machine you own or administer. From a terminal with Git installed:

```bash
git clone https://github.com/hey-nawazsharif/Linux-IT-diagnostics-toolkit.git
cd Linux-IT-diagnostics-toolkit
python3 -m opspulse --out-dir reports
```

No root privileges, no Python pip dependencies, and no network probes by default. If the repository has already been cloned, run only the last command from its root.

Creates:

- `reports/index.html` — self-contained report, open it in a browser.
- `reports/report.json` — structured data with an ordered `action_plan` for ticket documentation.

The HTML report lists **Critical → Attention → Not Verified** findings with suggested read-only investigation steps. A skipped backup check is not proof that a restore succeeded. The JSON contains only point-in-time results; it is not a live monitoring feed.

Optional tests (explicitly opt in to external DNS/TCP and service state checks):

```bash
python3 -m opspulse --dns example.com --tcp example.com --port 443 --service ssh --out-dir reports
```

**Network notice:** The optional network probes contact the host you specify, and they can generate logs on that destination; use approved targets only. `--service ssh` checks the **local** machine. If systemd is unavailable, the check reports skipped. By default, no external network connections are attempted.

## Interactive demo from any laptop or iPhone browser

**Public interactive demonstration:** https://hey-nawazsharif.github.io/Linux-IT-diagnostics-toolkit/

The GitHub Pages app (`docs/index.html` + `docs/app.js`) now provides:

The browser UI uses a compact, light IT operations-console layout. **It is a simulated demonstration and local JSON viewer, not a remote diagnostic website.** Desktop beta downloads are linked from the console and releases page.

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

Open `reports/demo/index.html` locally. The CLI now **refuses to overwrite the interactive `docs/index.html` dashboard** if you accidentally choose `--out-dir docs`.

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
    +-- collector.py       /proc, /sys, statvfs; optional DNS/TCP/systemctl
    +-- triage.py          Human-readable next checks ordered by priority
    +-- render.py          HTML escaping, self-contained CSS, safety labels
    +-- reports/index.html Openable offline in a browser
    +-- reports/report.json Structured ticket-friendly report
```

## Privacy and safety

- Read-only system observations. Does not run a vulnerability scan, alter files, kill processes or change service settings.
- Collects no usernames, IP addresses, MAC addresses, environment variables, authentication secrets or raw process command lines.
- The report contains explicitly requested DNS/TCP destination hostnames and service names. Do not use private customer names for public sample reports.
- **Never publish an unreviewed live report:** operational data may be confidential. CI builds and smoke-tests the desktop app on disposable runners but does not publish their real host reports. Only demo data is displayed publicly on GitHub Pages.
- Memory and inode thresholds are illustrative operating guidelines, not universal standards. Linux load average is not CPU-use percentage; a disk-space report is not a SMART test.
- Swap allocation by itself is **informational**, not evidence of active swapping or low available memory. An inode shortage can prevent file creation even when disk bytes remain free.
- Guidance is human triage, **never an automatic restart, deletion, scanning action or verified root cause**.
- RAID is not backup; this tool does not assert that backup restoration succeeded.

## Test

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q opspulse tests
```

CI in `.github/workflows/ci.yml` runs Python and Node browser tests. `.github/workflows/desktop-beta.yml` builds Windows, macOS Apple Silicon, macOS Intel and Linux developer previews, executes packaged collector smoke tests and publishes unsigned public prereleases if all jobs pass. Reports gathered on GitHub-hosted runners are never uploaded as artifacts.

## Roadmap

- [x] Read-only Linux system diagnostics
- [x] Responsive offline HTML and JSON reports
- [x] Unit tests, GitHub Actions example
- [x] Interactive GitHub Pages simulated scenarios, report filtering and local JSON viewer
- [x] Read-only filesystem inode and swap checks, triage action plans in real Linux HTML/JSON reports
- [x] Guard against accidentally replacing the published dashboard with CLI report output
- [ ] Optional alert threshold configuration and recurring health history
- [x] Windows/macOS `psutil`-based local collector, desktop GUI and four-OS build workflow
- [ ] Real-user physical-device testing, code signing/notarisation and OS-compatibility hardening
- [ ] Dashboard UI for multiple **authorised** hosts and ticket history
- [ ] Production hardening, benchmarks, and broader distro validation

## License

MIT. Educational project, no warranties. Author: Nawaz Sharif.