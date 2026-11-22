# OpsPulse desktop beta — Windows, macOS and Linux

**Status:** public developer preview. The application is an unsigned, open-source, local-only diagnostic tool. It is **not** a security scanner, malware remover, disk repair program, or production monitoring agent. The OS builds are tested in temporary GitHub Actions environments; normal device-by-device installation and usability testing is still required.

## How to download a desktop build

1. Open the [GitHub Releases](https://github.com/hey-nawazsharif/Linux-IT-diagnostics-toolkit/releases) page.
2. Open the newest **OpsPulse cross-platform desktop beta (unsigned)** prerelease.
3. Under **Assets**, download the matching build:
   - **MacBook M1/M2/M3/M4, etc.**: `OpsPulse-macos-apple-silicon-unsigned.zip`
   - **Mac Intel**: `OpsPulse-macos-intel-unsigned.zip`
   - **Windows PC (64-bit Intel/AMD)**: `OpsPulse-windows-x64-unsigned.zip`
   - **Linux desktop (64-bit x86)**: `OpsPulse-linux-x64-unsigned.tar.gz`
4. Compare the downloaded file's SHA-256 checksum against its corresponding `.sha256` asset before running it.
5. Unzip/extract it and open OpsPulse. Mac builds contain `OpsPulse.app`; Windows contains `OpsPulse.exe`; Linux contains `OpsPulse` binary.
6. Click **Run health check**. No scan begins before that click. Review results, and optionally use **Save HTML + JSON** to choose a local folder.
7. If you wish, open the public [report viewer](https://hey-nawazsharif.github.io/Linux-IT-diagnostics-toolkit/) and choose **Open a JSON report from your device** to inspect the saved `report.json`. File parsing stays in the browser. No server upload happens.

**Unsigned application warning:** Mac Gatekeeper and Windows SmartScreen may block unsigned programs. We do not supply a signed developer certificate or macOS notarisation. Do not disable system-wide protections or bypass company IT policy. Review source and build provenance first; if workplace security policy prohibits unsigned executables, use the Python source with approval or wait for a signed version.

**Apple Silicon build:** `macos-15` GitHub runner is ARM64; Mac Intel uses `macos-15-intel`. Neither is a test on your personal MacBook.

## If no release exists yet

Automated builds are defined in `.github/workflows/desktop-beta.yml`. Open the repository's **Actions → Cross-platform desktop beta — build and smoke test** workflow. A public prerelease is created **only if all four OS build and packaged-binary smoke jobs succeed**. If a build fails, no complete release is published; inspect the workflow logs rather than claiming downloads are ready.

## Run from Python source (no packaging required)

Install Python 3.11 or later and Git on your own machine. In a terminal/PowerShell:

```bash
git clone https://github.com/hey-nawazsharif/Linux-IT-diagnostics-toolkit.git
cd Linux-IT-diagnostics-toolkit
python -m pip install -r requirements-desktop.txt
python -m opspulse.desktop
```

On Linux, `python3` may be the executable name instead of `python`. Tkinter is included with many Python distributions but can require the OS's Tk package. The packaged builds include Python and the application's dependencies; they do not normally need a separate Python installation.

For a direct CLI report on **Windows/macOS/Linux**:

```bash
python -m opspulse --out-dir reports
```

The default CLI includes **no outbound DNS/TCP probes**. When deliberately requested on an approved destination only, `--dns example.com` or `--tcp example.com --port 443` enables network checks. The desktop GUI does **not** expose these optional probes yet.

## Privacy and limitations

- Local operation only. No accounts, cloud API, analytics, remote connection, running daemon, root/admin requirement, or modification of system configuration.
- Read-only local CPU, RAM, system-drive capacity, swap/pagefile, uptime and network interface *states*. No password, running-process inventory, IP/MAC address or network interface names are collected.
- Windows and macOS lack Linux-style `systemd` and inode checks in this version: those checks are displayed as **Not applicable / Not verified**, not false healthy results.
- This tool captures a **point-in-time** health report, not an ongoing monitor or vulnerability audit. CPU percentages are brief samples and can't diagnose a root cause.
- Any exported file stays local until you deliberately upload or share it; a report still can contain operational information. Review privacy and organisational policy first.
- The public website is a simulated demo and a local JSON viewer. **Opening the website alone cannot scan your device**.
- Software signing, installation experience, supported OS versions, and real-device validation remain beta work.

## Test and verify yourself

```bash
python -m unittest discover -s tests -v
python -m compileall -q opspulse
```

GitHub Actions independently executes tests and real local diagnostics on temporary Windows, macOS Apple Silicon, macOS Intel and Linux runners; it packages the GUI, then runs `--self-test` on each build without uploading its host's report.
