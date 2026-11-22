/* OpsPulse browser dashboard.
 * No remote diagnostics, no telemetry, no uploads.
 * All demo data are simulated. Imported JSON stays in this browser.
 */
(function () {
  "use strict";
  const STATUSES = ["pass", "warn", "critical", "info", "skip"];
  const TITLES = {pass:"Healthy",warn:"Attention",critical:"Critical",info:"Information",skip:"Not verified"};
  const CLASSIFY = {cpu:"CPU",ram:"Memory",disk:"Storage",uptime:"System",interfaces:"Network",dns:"Network",service:"Service",backup:"Backup"};
  const RECOMMENDATIONS = {
    cpu: "If sustained load is high, compare load average with logical CPUs and inspect processes, logs and I/O waits. Load is not CPU-utilisation percentage.",
    ram: "Review memory pressure, Linux available memory, application usage and swap behaviour. Avoid making changes without a maintenance plan.",
    disk: "Review capacity trends, log retention and large files before deleting anything. Disk usage is not a SMART health or backup check.",
    uptime: "Review boot history and change windows. Uptime alone does not indicate a healthy or secure system.",
    interfaces: "Confirm the expected interfaces are up and check approved network paths. Interface count is not an end-to-end connectivity test.",
    dns: "Compare configured DNS resolution and the application's required hostname. DNS resolution alone does not prove service availability.",
    service: "Check the relevant systemd service status, recent logs and application-level health. Active status alone cannot prove end-to-end function.",
    backup: "Restore an independent backup to an isolated test environment and document results. This dashboard never verifies backup recovery."
  };
  function cleanText(value, cap) {
    if (typeof value !== "string") throw new Error("Each report field must be text.");
    if (value.length > cap) throw new Error("Report field exceeds length limit.");
    return value;
  }
  function normalizeReport(input) {
    if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("Expected a JSON report object.");
    if (!Array.isArray(input.checks) || input.checks.length === 0 || input.checks.length > 100) {
      throw new Error("Report must contain between 1 and 100 checks.");
    }
    const checks = input.checks.map((raw, index) => {
      if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("Invalid check at position " + (index + 1));
      if (!STATUSES.includes(raw.status)) throw new Error("Unknown status in check " + (index + 1));
      return {
        key: cleanText(raw.key, 80),
        label: cleanText(raw.label, 160),
        status: raw.status,
        value: cleanText(raw.value, 500),
        detail: cleanText(raw.detail, 1200),
        category: cleanText(raw.category, 80)
      };
    });
    const summary = Object.fromEntries(STATUSES.map(status => [status, checks.filter(x => x.status === status).length]));
    return {
      schema_version: typeof input.schema_version === "string" ? input.schema_version.slice(0, 40) : "1.0",
      tool: typeof input.tool === "string" ? input.tool.slice(0, 100) : "OpsPulse",
      mode: typeof input.mode === "string" ? input.mode.slice(0, 90) : "UNSPECIFIED",
      generated_utc: typeof input.generated_utc === "string" ? input.generated_utc.slice(0, 90) : "",
      privacy: typeof input.privacy === "string" ? input.privacy.slice(0, 500) : "",
      network_probes: typeof input.network_probes === "string" ? input.network_probes.slice(0, 500) : "",
      checks, summary
    };
  }
  function scenarioReport(seed, scenario, now) {
    if (!["baseline", "healthy", "disk", "critical"].includes(scenario)) throw new Error("Unknown demo scenario");
    const report = normalizeReport(JSON.parse(JSON.stringify(seed)));
    const changed = Object.fromEntries(report.checks.map(x => [x.key, x]));
    if (scenario !== "baseline") {
      function update(key, status, value, detail) {
        if (!changed[key]) throw new Error("Missing demo sample check: " + key);
        Object.assign(changed[key], {status, value, detail: "[SIMULATED] " + detail});
      }
      update("cpu", "pass", "0.38 load / 8 logical CPUs", "Example 1-minute load is low relative to eight logical processors.");
      update("ram", "pass", "36.0% in use", "Example 16 GiB system has 64% available memory.");
      update("disk", "pass", "48.0% used", "Example root filesystem has ample free space.");
      update("uptime", "info", "6 days, 2 hours", "Illustrative time since last boot.");
      update("interfaces", "pass", "2 up / 2 non-loopback", "Example network interfaces are operational; application reachability is not tested.");
      update("dns", "pass", "Resolved (sample)", "DNS success is fictional; no request was sent.");
      update("service", "pass", "Active (sample)", "Sample SSH service flag, not an actual systemctl result.");
      update("backup", "skip", "Not verified", "A restore test is not simulated as evidence of recoverability.");
      if (scenario === "disk") {
        update("disk", "warn", "91.0% used", "High disk capacity usage could need a review of logs, backup policies and growth.");
        update("ram", "warn", "88.0% in use", "High memory use is a warning example; investigate actual available memory and workload.");
      }
      if (scenario === "critical") {
        update("cpu", "warn", "11.50 load / 8 logical CPUs", "Sustained pressure might merit process, storage and I/O investigation.");
        update("ram", "critical", "98.0% in use", "Example memory pressure exceeds the demo's threshold; a real Linux machine was not checked.");
        update("disk", "critical", "98.0% used", "Example filesystem has very little free space; capacity planning is urgent.");
        update("interfaces", "warn", "0 up / 2 non-loopback", "Example physical interfaces are down; no local network access was attempted.");
        update("dns", "warn", "Resolution failed (sample)", "Fictional DNS failure; no domain was queried.");
        update("service", "warn", "Inactive (sample)", "Fictional service state, not tested.");
      }
    }
    report.mode = "SIMULATED DEMO";
    report.generated_utc = now || new Date().toISOString();
    report.network_probes = "SIMULATED — the browser did not probe any machine or network.";
    report.summary = Object.fromEntries(STATUSES.map(status => [status, report.checks.filter(c => c.status === status).length]));
    return report;
  }
  const api = {normalizeReport, scenarioReport, STATUSES, TITLES};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof document === "undefined") return;

  document.addEventListener("DOMContentLoaded", function () {
    const $ = id => document.getElementById(id);
    const initial = JSON.parse($("seed-report").textContent);
    const state = {report: scenarioReport(initial,"baseline",initial.generated_utc), imported:false, filter:"all", query:"", downloadUrl:null};
    const mobileHint = document.getElementById("quick-result");
    function updateQuickResult() {
      const data=state.report.summary;
      mobileHint.textContent = state.imported
        ? "Imported file · " + data.critical + " critical · " + data.warn + " attention · " + data.pass + " healthy (unverified)"
        : "Simulation · " + data.critical + " critical · " + data.warn + " attention · " + data.pass + " healthy";
      mobileHint.dataset.level = data.critical ? "critical" : data.warn ? "warn" : "pass";
    }
    function showJsonText() {
      const preview = $("json-viewer");
      preview.hidden = false;
      $("json-data").value = JSON.stringify(state.report,null,2);
    }

    function safeNode(tag, cls, value) {
      const element = document.createElement(tag);
      if (cls) element.className = cls;
      if (value !== undefined) element.textContent = value;
      return element;
    }
    function message(value, type) {
      $("feedback").textContent = value;
      $("feedback").dataset.type = type || "info";
    }
    function counts() {
      const parent = $("stats");
      parent.replaceChildren();
      for (const status of STATUSES) {
        const card = safeNode("div","stat "+status);
        card.append(safeNode("strong","",String(state.report.summary[status])), safeNode("span","",TITLES[status]));
        parent.append(card);
      }
      $("count-line").textContent = state.report.checks.length + " checks in this report";
    }
    function makeCheck(check) {
      const card = safeNode("article","card");
      card.dataset.status = check.status;
      const top = safeNode("div","card-top");
      top.append(safeNode("h3","",check.label),safeNode("span","flag "+check.status,TITLES[check.status]));
      card.append(top,safeNode("div","value",check.value),safeNode("p","",check.detail));
      const details = document.createElement("details");
      details.className = "follow-up";
      details.append(safeNode("summary","","What should an IT engineer check?"));
      details.append(safeNode("p","",RECOMMENDATIONS[check.key] || "Review the system's logs, service requirements and documented support procedure before changes."));
      card.append(details);
      return card;
    }
    function cards() {
      const grid = $("diagnostic-grid");
      const query = state.query.toLowerCase();
      const filtered = state.report.checks.filter(c =>
        (state.filter === "all" || c.status === state.filter) &&
        [c.label,c.value,c.detail,c.category].join(" ").toLowerCase().includes(query)
      );
      grid.replaceChildren(...filtered.map(makeCheck));
      $("filtered-count").textContent = "Showing " + filtered.length + " of " + state.report.checks.length + " checks";
      $("empty").hidden = filtered.length !== 0;
    }
    function render() {
      counts(); cards(); updateQuickResult();
      $("mode-badge").textContent = state.imported ? "IMPORTED REPORT — UNVERIFIED" : "SIMULATED DEMO";
      $("mode-badge").className = "pill " + (state.imported ? "imported" : "demo");
      $("context").textContent = state.imported ?
        "This file was opened locally in your browser. It has NOT been verified or uploaded, and no live scan was performed. File-reported mode: " + state.report.mode + "." :
        "All diagnostics on this screen are fictional learning scenarios. The browser is NOT scanning your phone, this server, or any network.";
      $("updated").textContent = "Report time: " + (state.report.generated_utc || "unspecified") +
        " · " + (state.imported ? "local JSON import" : "simulated values");
      for (const button of document.querySelectorAll("[data-filter]")) {
        button.setAttribute("aria-pressed", String(button.dataset.filter === state.filter));
        const k=button.dataset.filter;
        button.textContent = k === "all" ? "All ("+state.report.checks.length+")" :
          TITLES[k] + " ("+state.report.summary[k]+")";
      }
    }
    function startScenario(selected) {
      state.report = scenarioReport(initial,selected);
      state.imported = false;
      state.filter = "all";
      state.query = "";
      $("search").value = "";
      render();
      message("Loaded " + $("scenario").selectedOptions[0].textContent +
        ". Counts above and results below have changed. This is simulated, not a hardware scan.","success");
    }
    $("run").addEventListener("click", () => startScenario($("scenario").value));
    $("scenario").addEventListener("change", () => {
      message("Selected: " + $("scenario").selectedOptions[0].textContent +
        ". Tap Run simulated diagnostics to update the result.","info");
    });
    $("reset").addEventListener("click", () => {
      $("scenario").value="baseline";
      $("report-file").value="";
      startScenario("baseline");
      message("Original fictional demo restored. No system scan was made.","success");
    });
    $("search").addEventListener("input", event => {state.query=event.target.value.trim();cards();});
    document.querySelectorAll("[data-filter]").forEach(button=>{
      button.addEventListener("click",()=>{state.filter=button.dataset.filter;render();});
    });
    $("report-file").addEventListener("change",async event=>{
      const file=event.target.files && event.target.files[0];
      if (!file) return;
      if (file.size > 1024*1024) {message("File is too large (maximum 1 MB).","error");event.target.value="";return;}
      try {
        // File.text() is supported in modern iOS Safari. Keep a FileReader fallback
        // for restricted in-app browsers that lack the method.
        const fileContent = typeof file.text === "function" ? await file.text() :
          await new Promise((resolve,reject) => {
            const reader=new FileReader();
            reader.onload=() => resolve(String(reader.result || ""));
            reader.onerror=() => reject(new Error("Could not read the selected file"));
            reader.readAsText(file);
          });
        const raw=JSON.parse(fileContent);
        const report=normalizeReport(raw);
        state.report=report;state.imported=true;state.filter="all";state.query="";
        $("search").value="";
        render();
        message("Imported " + report.checks.length +
          " checks from a local JSON file. This page did not verify that the file came from a real Linux machine.","success");
      } catch (error) {
        message("Unable to open report: " + String(error.message || error),"error");
      } finally {event.target.value="";}
    });
    $("export").addEventListener("click",()=>{
      const json=JSON.stringify(state.report,null,2)+"\n";
      const save=$("download-link");
      if (state.downloadUrl) URL.revokeObjectURL(state.downloadUrl);
      try {
        state.downloadUrl=URL.createObjectURL(new Blob([json],{type:"application/json"}));
        save.href=state.downloadUrl;
        save.download=state.imported ? "opspulse-imported-unverified.json" : "opspulse-simulated-demo.json";
        save.hidden=false;
        showJsonText();
        // iOS Safari sometimes ignores a programmatic download; leave an
        // accessible, user-tappable link and copyable JSON visible as fallback.
        save.click();
        message("Report ready. If no download appeared on iPhone, tap Save JSON file or copy the JSON below.","success");
      } catch(error) {
        showJsonText();
        message("Automatic download unavailable here. Copy the JSON text shown below.","error");
      }
    });
    $("view-json").addEventListener("click",()=>{
      const preview=$("json-viewer");
      if (preview.hidden) {showJsonText();message("Report JSON displayed below. You can select and copy it.","info");}
      else {preview.hidden=true;message("JSON preview closed.","info");}
    });
    window.addEventListener("pagehide",()=>{if(state.downloadUrl)URL.revokeObjectURL(state.downloadUrl);});
    $("print").addEventListener("click",()=>window.print());
    $("copy-command").addEventListener("click",async()=>{
      const cmd="python3 -m opspulse --out-dir reports";
      try {
        await navigator.clipboard.writeText(cmd);
        message("Linux diagnostic command copied. Run only on a Linux system you own or administer.","success");
      } catch (_) {
        const commandElement=$("linux-command");
        const range=document.createRange();
        range.selectNodeContents(commandElement);
        const selection=window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        message("Your browser blocked automatic copy. The command is selected—use Copy from the selection menu.","info");
      }
    });
    render();
    message("Interactive dashboard ready. Choose a scenario and tap Run simulated diagnostics, or import an authorised report JSON.","info");
  });
})();
