"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const app = require("../docs/app.js");
const sample = JSON.parse(fs.readFileSync(path.join(__dirname,"../docs/report.json"),"utf8"));
const html = fs.readFileSync(path.join(__dirname,"../docs/index.html"),"utf8");

test("base fictional report is explicitly simulated and internally consistent", () => {
  const r = app.scenarioReport(sample,"baseline","2026-11-22T00:00:00Z");
  assert.equal(r.mode,"SIMULATED DEMO");
  assert.equal(r.summary.warn,1);
  assert.equal(r.summary.critical,0);
  assert.equal(r.summary.skip,1);
  assert.equal(r.checks.length,8);
  assert.match(r.network_probes,/SIMULATED/);
});

test("healthy scenario actually alters values, removes warnings, never verifies backup", () => {
  const r = app.scenarioReport(sample,"healthy","2026-11-22T00:00:00Z");
  assert.equal(r.summary.pass,6);
  assert.equal(r.summary.warn,0);
  assert.equal(r.summary.critical,0);
  assert.equal(r.summary.skip,1);
  assert.equal(r.checks.find(x=>x.key==="disk").value,"48.0% used");
  assert.equal(r.checks.find(x=>x.key==="backup").status,"skip");
});

test("resource warning scenario actually creates disk and RAM warnings", () => {
  const r = app.scenarioReport(sample,"disk","2026-11-22T00:00:00Z");
  assert.equal(r.summary.warn,2);
  assert.equal(r.checks.find(x=>x.key==="ram").status,"warn");
  assert.equal(r.checks.find(x=>x.key==="disk").status,"warn");
});

test("critical scenario changes CPU, memory, disk, services and network", () => {
  const r = app.scenarioReport(sample,"critical","2026-11-22T00:00:00Z");
  assert.equal(r.summary.critical,2);
  assert.equal(r.summary.warn,4);
  assert.equal(r.checks.find(x=>x.key==="dns").status,"warn");
  assert.equal(r.checks.find(x=>x.key==="service").status,"warn");
  assert.equal(r.checks.find(x=>x.key==="backup").status,"skip");
});

test("all scenarios leave original seed unmodified", () => {
  const source = JSON.stringify(sample);
  ["healthy","disk","critical","baseline"].forEach(s=>app.scenarioReport(sample,s));
  assert.equal(JSON.stringify(sample),source);
});

test("file-import parser recomputes summary rather than trusting supplied values", () => {
  const modified = JSON.parse(JSON.stringify(sample));
  modified.summary={pass:9999,warn:0,critical:0,info:0,skip:0};
  const normalized=app.normalizeReport(modified);
  assert.equal(normalized.summary.pass,5);
  assert.equal(normalized.summary.warn,1);
  assert.equal(normalized.summary.skip,1);
});

test("parser rejects malformed or unsafe status schemas", () => {
  assert.throws(()=>app.normalizeReport({checks:[]}),/between 1 and 100/);
  assert.throws(()=>app.normalizeReport({checks:[{status:"execute"}]}),/Unknown status/);
  const malformed=JSON.parse(JSON.stringify(sample));
  malformed.checks[0].value={html:"<script>alert(1)</script>"};
  assert.throws(()=>app.normalizeReport(malformed),/must be text/);
  const oversized=JSON.parse(JSON.stringify(sample));
  oversized.checks[0].detail="a".repeat(1201);
  assert.throws(()=>app.normalizeReport(oversized),/exceeds length limit/);
});

test("browser demo contains all controls and explicit privacy limitations", () => {
  for (const id of ["seed-report","scenario","run","reset","report-file","export","view-json","json-viewer","json-data","download-link","quick-result","print","search","stats","diagnostic-grid","feedback","mode-badge","context","copy-command"]) {
    assert.match(html,new RegExp('id="'+id+'"'),"Missing browser control "+id);
  }
  assert.match(html,/src="\.\/app\.js\?v=20261122-3"/);
  assert.match(html,/SIMULATED DEMO/);
  assert.match(html,/not sent to GitHub/);
  assert.match(html,/cannot read your device/);
  assert.match(html,/github\.com\/hey-nawazsharif\/Linux-IT-diagnostics-toolkit/);
});

test("No external dashboard dependency or API integration", () => {
  const js=fs.readFileSync(path.join(__dirname,"../docs/app.js"),"utf8");
  assert.doesNotMatch(js,/\bfetch\(|XMLHttpRequest|sendBeacon|WebSocket/);
  assert.match(js,/textContent\s*=/); // imports rendered as text, not HTML
  assert.doesNotMatch(js,/\.innerHTML\s*=/);
  assert.match(js,/file\.text\(\)/);
});


test("iPhone Safari has a native file picker, visible result and manual download fallback", () => {
  assert.match(html,/class="native-file"/);
  assert.match(html,/id="download-link"[^>]*hidden/);
  assert.match(html,/id="quick-result"[^>]*role="status"/);
  assert.match(html,/v0\.3 · Mobile fixes/);
  const js=fs.readFileSync(path.join(__dirname,"../docs/app.js"),"utf8");
  assert.match(js,/download-link/);
  assert.match(js,/View.*JSON|json-viewer/);
  assert.match(js,/typeof file\.text === "function"/);
  assert.match(js,/FileReader/);
  assert.doesNotMatch(js,/setTimeout\(\(\)=>URL\.revokeObjectURL/);
});
