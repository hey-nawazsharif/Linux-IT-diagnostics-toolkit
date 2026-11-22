# OpsPulse — iPhone par interactive dashboard kaise use karein

**Project published:** https://github.com/hey-nawazsharif/Linux-IT-diagnostics-toolkit

**Live GitHub Pages demo:** https://hey-nawazsharif.github.io/Linux-IT-diagnostics-toolkit/

## iPhone par kya kaam karega?

1. Demo link Safari mein kholo.
2. **Diagnostic scenario** mein Healthy / Disk warnings / Critical load select karo.
3. **Run simulated diagnostics** dabao; CPU, memory, disk, service status aur alerts us fictional scenario ke hisaab se badlenge.
4. **Healthy / Attention / Critical** filters ya **Search** ka use karke specific diagnostics dekho.
5. Har card ke neeche **What should an IT engineer check?** se troubleshooting guidance dekho.
6. **Download JSON** se current scenario ka local sample file save kar sakte ho.
7. **Reset demo** se original fictional values wapas aa jayengi.

**Zaruri:** Ye browser demo hai. Ye iPhone, Mac ya kisi remote Linux machine ko scan nahi karta; sab initial values SIMULATED hain.

## Real Linux JSON report ko dekhna

Agar kisi authorised Linux machine par Python 3.11+ installed hai aur is repo ka code hai:

```bash
python3 -m opspulse --out-dir reports
```

Us Linux machine ki `reports/report.json` file ko iPhone mein locally transfer karo (only after checking security/privacy approval), phir dashboard par **Open a local JSON report** choose karo. Browser data ko kisi server par upload nahi karta; local file ka source aur accuracy verify karna tumhari zimmedari hai.

## GitHub Actions

GitHub CI checks: https://github.com/hey-nawazsharif/Linux-IT-diagnostics-toolkit/actions

GitHub Actions Linux runner par tests run karta hai; ye tumhara phone ya personal computer scan nahi karta.

## Privacy

- Browser demo: no external analytics or data-submission API.
- JSON file import: browser mein locally parse hoti hai. 1 MB file-size limit.
- **SIMULATED DEMO** = fictional data; **IMPORTED REPORT — UNVERIFIED** = user-supplied file with no automatic authentication.
- Never publish real office/server diagnostic reports without authorization.

## LinkedIn

Project ka public title **OpsPulse — Linux IT Diagnostics Toolkit** rakho.
Demonstration link ko **Interactive Simulated Demo** hi describe karo; production/live monitoring claim mat karo.
