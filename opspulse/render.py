"""Self-contained, accessible, privacy-conscious HTML report renderer."""
from __future__ import annotations

from html import escape
from typing import Any

from .triage import action_plan

STATUS_TEXT = {"pass": "Healthy", "warn": "Attention", "critical": "Critical", "info": "Information", "skip": "Not verified"}

STYLE = """
:root { color-scheme: dark; --bg:#07111e; --panel:#102034; --panel2:#132940; --line:#284052; --text:#e8f1f9; --muted:#9fb7c8; --accent:#73d8c9; --warn:#f4c17a; --crit:#f7a0a0; --info:#9dc3f7; }
* { box-sizing:border-box } html { scroll-behavior:smooth }
body { margin:0; background:radial-gradient(circle at 84% -3%,#123c47 0,transparent 40%),var(--bg); color:var(--text); font:16px/1.65 system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }
a { color:var(--accent); } .container { width:min(1080px,calc(100% - 36px));margin:auto; }
header { border-bottom:1px solid var(--line);padding:23px 0; }.brand { font-weight:800;letter-spacing:.055em;font-size:20px; }.brand span { color:var(--accent); }
.hero { padding:62px 0 29px; }.eyebrow{font-size:12px;letter-spacing:.17em;text-transform:uppercase;color:var(--accent);font-weight:700;}
h1{font-size:clamp(29px,5vw,50px);line-height:1.15;letter-spacing:-.025em;margin:12px 0 18px;max-width:790px;} .lead{max-width:790px;color:#b8ccd9;font-size:18px;} .pill{border:1px solid #507989;color:#d7fffa;padding:5px 11px;border-radius:25px;font-size:12px;font-weight:750;display:inline-block}
.pill.demo{border-color:#d1a153;color:#ffe4a8;} .meta{color:var(--muted);font-size:13px;margin-top:18px;}
.stats{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:18px 0 35px;}.stat{border:1px solid var(--line);background:var(--panel);padding:18px;border-radius:13px;}.stat strong{display:block;font-size:34px;line-height:1.15}.stat span{font-size:12px;color:var(--muted);}.stat.critical strong{color:var(--crit)}.stat.warn strong{color:var(--warn)}.stat.pass strong{color:var(--accent)}
.section-title{font-size:23px;margin:42px 0 10px;letter-spacing:-.02em;}.intro{color:var(--muted);margin-top:0}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;}.card{min-width:0;border:1px solid var(--line);background:var(--panel);border-radius:13px;padding:21px 22px;}.card-top{display:flex;justify-content:space-between;align-items:start;gap:10px;}.card h3{font-size:16px;margin:0 0 12px;}.card .value{font-size:22px;line-height:1.35;font-weight:760;overflow-wrap:anywhere;}.card p{font-size:14px;color:var(--muted);line-height:1.65;margin:11px 0 0;overflow-wrap:anywhere;}.flag{white-space:nowrap;border-radius:6px;padding:4px 8px;font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.04em;}.flag.pass{color:#83ebd7;background:#174239}.flag.warn{color:#ffe1a9;background:#473520}.flag.critical{color:#ffc3c3;background:#4a282c}.flag.skip,.flag.info{color:#d4e4f7;background:#293f53}
.callout{background:var(--panel2);border-left:3px solid var(--accent);padding:17px 19px;margin:22px 0;border-radius:5px;font-size:14px;color:#bfd7e4;}.callout strong{color:white}.note-list{padding-left:23px;color:#b3cbd8}.note-list li{padding:5px 0}footer{border-top:1px solid var(--line);color:var(--muted);font-size:13px;margin-top:48px;padding:22px 0 36px;}footer .container{display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px}
.triage-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px;margin:16px 0 32px}
.triage-item{border:1px solid var(--line);border-radius:12px;padding:20px 22px;background:var(--panel);break-inside:avoid}
.triage-item.critical{border-left:4px solid var(--crit)}.triage-item.warn{border-left:4px solid var(--warn)}
.triage-item.verification{border-left:4px solid var(--info)}
.triage-item h3{font-size:16px;margin:0 0 10px}.triage-item .evidence{font-size:13px;color:var(--muted);margin:0}
.triage-item ol{padding-left:21px;font-size:14px;color:#c7dae4;line-height:1.7;margin-bottom:0}
.triage-item li{padding:4px 0}.triage-lead{font-size:14px;color:var(--muted)}
@media(max-width:820px){.triage-list{grid-template-columns:1fr}}@media(max-width:820px){.stats{grid-template-columns:repeat(3,1fr)}}@media(max-width:630px){.hero{padding-top:38px}.stats{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}.card{padding:19px}.stat strong{font-size:29px}.stat{padding:14px}}
@media print{body{background:white;color:#111}.card,.stat,.callout{background:#f7f9fa;color:#111;border-color:#d2d9df;break-inside:avoid}.card p,.lead,.intro,.stat span,.meta,.note-list,footer{color:#444}.eyebrow,.brand span{color:#165850}.flag{color:#111!important;background:#eef1f2!important}header{border-color:#ccc}}
"""


def render_html(report: dict[str, Any]) -> str:
    mode = str(report["mode"])
    is_demo = mode == "SIMULATED DEMO"
    summary = report["summary"]
    cells = []
    for item in report["checks"]:
        status = str(item["status"])
        if status not in STATUS_TEXT:
            status = "skip"
        cells.append(
            '<article class="card">'
            '<div class="card-top"><h3>' + escape(str(item["label"])) + '</h3>'
            '<span class="flag ' + escape(status) + '">' + escape(STATUS_TEXT[status]) + '</span></div>'
            '<div class="value">' + escape(str(item["value"])) + '</div>'
            '<p>' + escape(str(item["detail"])) + '</p></article>'
        )
    cards = "\n".join(cells)
    # The HTML is self-contained. Recommendations are read-only follow-ups,
    # not automated remediation; all human-readable data are escaped.
    followups = report.get("action_plan") or action_plan(report["checks"])
    plan_cards = []
    for item in followups:
        priority = str(item.get("priority", "verification"))
        if priority not in {"critical", "warn", "verification"}:
            priority = "verification"
        heading = {"critical": "Critical", "warn": "Attention", "verification": "Not verified"}[priority]
        steps = "".join("<li>" + escape(str(step)) + "</li>" for step in item.get("next_steps", []))
        plan_cards.append(
            '<article class="triage-item ' + priority + '"><h3>' +
            escape(heading) + " · " + escape(str(item.get("label", "Check"))) +
            '</h3><p class="evidence">Observed: ' + escape(str(item.get("observed", "Unknown"))) +
            '</p><ol>' + steps + '</ol></article>'
        )
    plan_html = "\n".join(plan_cards) if plan_cards else (
        '<p class="callout">No warnings or critical checks were reported. '
        'This does not establish that the machine or backups are fully healthy.</p>'
    )
    stats = "".join(
        '<div class="stat ' + stat + '"><strong>' + str(int(summary.get(stat, 0))) + '</strong><span>' + title + '</span></div>'
        for stat, title in (("pass", "Healthy"), ("warn", "Attention"), ("critical", "Critical"), ("info", "Informational"), ("skip", "Not verified"))
    )
    banner = "This is simulated sample data. No real server, network or backups were tested." if is_demo else "This report summarises point-in-time checks of the Linux machine where the command ran. It is not a complete security audit."
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="OpsPulse: example or read-only Linux system health checks with an accessible diagnostic report.">
<meta name="robots" content="noindex,nofollow"><title>OpsPulse — Linux IT Diagnostics</title>
<style>{STYLE}</style></head>
<body><header><div class="container"><div class="brand">Ops<span>Pulse</span> <small style="font-weight:500;font-size:13px;color:#a5c1cf">/ Linux IT Diagnostics</small></div></div></header>
<main class="container"><section class="hero" aria-labelledby="page-title"><div class="eyebrow">Read-only system health overview</div>
<h1 id="page-title">Understand a Linux machine at a glance.</h1><p class="lead">Quick health signals for CPU load, available memory, filesystem capacity, network interface state and basic system services—without privileged access or hidden scans.</p>
<span class="pill {'demo' if is_demo else ''}">{escape(mode)}</span>
<p class="meta">Report generated (UTC): {escape(str(report["generated_utc"]))} · Python standard library · Version {escape(str(report["schema_version"]))}</p></section>
<div class="callout"><strong>Report context:</strong> {escape(banner)}</div>
<section aria-labelledby="overview"><h2 class="section-title" id="overview">Overview</h2><div class="stats">{stats}</div></section>
<section aria-labelledby="checks"><h2 class="section-title" id="checks">Diagnostics</h2>
<p class="intro">Warnings indicate possible attention areas, not proof of a root cause. Follow up with relevant logs and operational evidence.</p>
<div class="grid">{cards}</div></section>
<section aria-labelledby="action-plan"><h2 class="section-title" id="action-plan">Recommended troubleshooting next steps</h2>
<p class="triage-lead">Ordered by critical, attention and not-verified checks. Suggestions are read-only investigative actions, not automated repairs or proof of root cause.</p>
<div class="triage-list">{plan_html}</div></section>
<section aria-labelledby="safety"><h2 class="section-title" id="safety">How to interpret this report</h2>
<ul class="note-list"><li>Local Linux checks are read-only. DNS, TCP and systemd service checks run only when requested.</li>
<li>Disk capacity is not a SMART drive-health test; service status does not establish end-to-end application health.</li>
<li>A successful report does <strong>not</strong> prove backups are recoverable. Conduct a separate restore test.</li>
<li>{escape(str(report["privacy"]))}</li>
<li>{escape(str(report["network_probes"]))}</li></ul></section></main>
<footer><div class="container"><span>OpsPulse · Open-source Linux IT Diagnostics Toolkit</span><span>Static HTML · No cookies, external scripts or analytics</span></div></footer></body></html>'''