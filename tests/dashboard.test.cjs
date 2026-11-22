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
  for (const id of ["seed-report","scenario","run","reset","report-file","export","view-json","json-viewer","json-data","download-link","quick-result","action-plan-list","action-summary","print","search","stats","diagnostic-grid","feedback","mode-badge","context","copy-command"]) {
    assert.match(html,new RegExp('id="'+id+'"'),"Missing browser control "+id);
  }
  assert.match(html,/src="\.\/app\.js\?v=20261123-1"/);
  assert.match(html,/SIMULATED DEMO/);
  assert.match(html,/not uploaded to a server/);
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
  assert.match(html,/v0\.5/);
  const js=fs.readFileSync(path.join(__dirname,"../docs/app.js"),"utf8");
  assert.match(js,/download-link/);
  assert.match(js,/View.*JSON|json-viewer/);
  assert.match(js,/typeof file\.text === "function"/);
  assert.match(js,/FileReader/);
  assert.doesNotMatch(js,/setTimeout\(\(\)=>URL\.revokeObjectURL/);
});


test("scenario changes recompute priority-ordered actionable follow-up items", () => {
  const healthy=app.scenarioReport(sample,"healthy","2026-11-22T00:00:00Z");
  assert.equal(healthy.action_plan.length,1);
  assert.equal(healthy.action_plan[0].priority,"verification");
  assert.equal(healthy.action_plan[0].check_key,"backup");
  const critical=app.scenarioReport(sample,"critical","2026-11-22T00:00:00Z");
  assert.deepEqual(critical.action_plan.slice(0,2).map(x=>x.priority),["critical","critical"]);
  assert.equal(critical.action_plan.at(-1).priority,"verification");
  assert.ok(critical.action_plan[0].next_steps.length > 0);
  assert.equal(critical.action_plan[0].observed,"98.0% in use");
});

test("import preserves validated real Linux actionable triage recommendations", () => {
  const imported=JSON.parse(JSON.stringify(sample));
  imported.mode="LIVE LOCAL LINUX";
  imported.action_plan=[{
    check_key:"inodes",label:"Filesystem inode availability",priority:"critical",
    observed:"99.0% used",next_steps:["Run df -i locally","Review small-file retention"]
  }];
  const result=app.normalizeReport(imported);
  assert.equal(result.action_plan.length,1);
  assert.equal(result.action_plan[0].priority,"critical");
  assert.equal(result.action_plan[0].check_key,"inodes");
  assert.match(result.action_plan[0].next_steps[0],/df -i/);
  imported.action_plan[0].next_steps=["x".repeat(901)];
  assert.throws(()=>app.normalizeReport(imported),/exceeds length limit/);
  imported.action_plan[0].next_steps=[];
  imported.action_plan[0].priority="admin";
  assert.throws(()=>app.normalizeReport(imported),/Invalid action plan entry/);
});

test("new Linux diagnostics have safe local recommendations", () => {
  const js=fs.readFileSync(path.join(__dirname,"../docs/app.js"),"utf8");
  for(const id of ["inodes","swap","tcp"]) assert.match(js,new RegExp("    "+id+":"));
  assert.match(html,/id="triage-title"/);
  assert.match(html,/schema_version":"1\.1"/);
});


test("v0.5 is an accessible, compact operations console instead of a decorative landing page", () => {
  assert.match(html,/color-scheme:light/);
  assert.match(html,/class="app"/);
  assert.match(html,/class="rail"/);
  assert.match(html,/id="workspace"/);
  assert.match(html,/class="topbar"/);
  assert.match(html,/id="report-tools"/);
  assert.match(html,/id="findings"/);
  assert.match(html,/id="run-guide"/);
  assert.match(html,/role="note"/);
  assert.match(html,/href="#workspace"/);
  assert.match(html,/Skip to diagnostic workspace/);
  assert.match(html,/text-underline-offset/);
  assert.doesNotMatch(html,/radial-gradient/);
  assert.doesNotMatch(html,/Explore Linux diagnostics\. Understand the signals/);
  assert.match(html,/This workspace is showing fictional learning data/);
});
