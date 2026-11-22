#!/usr/bin/env python3
"""Headless browser smoke test: exercise actual DOM click handlers, not just static markup.

Runs only on authorised CI runner; does not scan host, use the network, or publish reports.
"""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "index.html"
SCRATCH = ROOT / "docs" / "_temporary_ui_smoke.html"

TEST_JS = r"""
<script>
window.addEventListener('load', async function () {
  try {
    const get = id => document.getElementById(id);
    const check = (ok, msg) => { if (!ok) throw new Error(msg); };
    check(document.querySelectorAll('#diagnostic-grid article').length === 8, 'initial cards missing');
    check(get('mode-badge').textContent.includes('SIMULATED DEMO'), 'initial demo label');

    get('scenario').value = 'critical';
    get('run').click();
    check(document.querySelector('#stats .stat.critical strong').textContent === '2', 'critical scenario count');
    check(get('diagnostic-grid').textContent.includes('98.0% in use'), 'critical RAM value not rendered');

    document.querySelector('[data-filter="critical"]').click();
    check(document.querySelectorAll('#diagnostic-grid article').length === 2, 'status filter not working');

    document.querySelector('[data-filter="all"]').click();
    get('search').value = 'backup';
    get('search').dispatchEvent(new Event('input',{bubbles:true}));
    check(document.querySelectorAll('#diagnostic-grid article').length === 1, 'search not working');
    check(get('diagnostic-grid').textContent.includes('Not verified'), 'backup never verified');

    get('reset').click();
    check(document.querySelectorAll('#diagnostic-grid article').length === 8, 'reset cards');
    check(document.querySelector('#stats .stat.warn strong').textContent === '1', 'reset warning count');

    const upload = get('report-file');
    const mock = JSON.parse(get('seed-report').textContent);
    mock.mode = 'LIVE LOCAL LINUX';
    mock.checks[0].value = '2.11 load / 4 logical CPUs';
    const file = new File([JSON.stringify(mock)], 'report.json',{type:'application/json'});
    const dt = new DataTransfer(); dt.items.add(file);
    upload.files = dt.files;
    upload.dispatchEvent(new Event('change',{bubbles:true}));
    await new Promise(resolve => setTimeout(resolve,120));
    check(get('mode-badge').textContent.includes('IMPORTED REPORT'), 'imported label');
    check(get('context').textContent.includes('NOT been verified'), 'unverified context label');
    check(get('diagnostic-grid').textContent.includes('2.11 load'), 'import not rendered');

    get('export').click();
    check(get('feedback').textContent.includes('download'), 'download action missing');
    document.body.setAttribute('data-opspulse-smoke','PASS');
  } catch (e) {
    document.body.setAttribute('data-opspulse-smoke','FAIL');
    document.body.setAttribute('data-opspulse-smoke-error', String(e.message || e));
  }
});
</script>
"""

def main() -> None:
    chrome = (shutil.which("google-chrome") or shutil.which("chromium") or
              shutil.which("chromium-browser"))
    if not chrome:
        raise SystemExit("No headless Chrome/Chromium installed; browser smoke not run")
    original = PAGE.read_text(encoding="utf-8")
    assert original.count("</body>") == 1
    SCRATCH.write_text(original.replace("</body>", TEST_JS + "\n</body>"), encoding="utf-8")
    try:
        result = subprocess.run(
            [chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
             "--disable-dev-shm-usage", "--no-first-run", "--no-default-browser-check",
             "--allow-file-access-from-files", "--virtual-time-budget=7000",
             "--dump-dom", SCRATCH.as_uri()],
            capture_output=True, text=True, timeout=35, check=False,
        )
        if 'data-opspulse-smoke="PASS"' not in result.stdout:
            import re
            match = re.search(r'data-opspulse-smoke-error="([^"]+)"',result.stdout)
            print((match.group(1) if match else result.stdout[-2500:]) or result.stderr[-2500:])
            raise SystemExit("FAIL: Browser did not complete scenario, search, reset, import and download actions")
        print("PASS: headless browser tested all major OpsPulse interactive controls")
    finally:
        SCRATCH.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
