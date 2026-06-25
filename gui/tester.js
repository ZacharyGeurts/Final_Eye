/* Final_Eye Field Ops — single page, AI/robotics first, all details */
(function () {
  "use strict";

  const POLL_MS = 2500;
  const SECTION_META = {
    robotics: { title: "01 · Robotics", sub: "modes · rig · stream · video · contract" },
    ai: { title: "02 · AI & Compiler", sub: "Grok16 · neural · GRKMF · field compiler" },
    weapons: { title: "03 · Weapons Arsenal", sub: "racks · salvo · threat map · entity state" },
    entity: { title: "04 · Entity Eyeballs", sub: "Vita · Veritas · twins · forward ledger" },
    vision: { title: "05 · Vision Ingress", sub: "preserve · offense · pattern · vigilance" },
    truth: { title: "06 · Truth & Trust", sub: "heaven/hell · IRTN · Hostess7 · co-pilot" },
    field: { title: "07 · Field Authority", sub: "mandate · kill · seal · sovereign · HUD" },
    integration: { title: "08 · Integration", sub: "ZAC · Queen · Hostess7 · environment" },
  };

  let pollTimer = null;
  const $ = (id) => document.getElementById(id);

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function fmt(v) {
    if (v === null || v === undefined) return "—";
    if (typeof v === "boolean") return v ? "yes" : "no";
    if (typeof v === "object") return JSON.stringify(v);
    return String(v);
  }

  async function fetchJson(url) {
    const r = await fetch(url, { cache: "no-store" });
    return r.json();
  }

  function flattenRows(obj, prefix, out, depth) {
    if (depth > 5 || obj === null || obj === undefined) return;
    if (Array.isArray(obj)) {
      out.push({ k: prefix, v: "[" + obj.length + " items] " + JSON.stringify(obj).slice(0, 200) });
      return;
    }
    if (typeof obj !== "object") {
      out.push({ k: prefix, v: fmt(obj) });
      return;
    }
    const keys = Object.keys(obj);
    if (keys.length > 24 && depth > 0) {
      out.push({ k: prefix, v: "{" + keys.length + " keys}" });
      return;
    }
    for (const key of keys.slice(0, 60)) {
      if (key.startsWith("_")) continue;
      const p = prefix ? prefix + "." + key : key;
      const val = obj[key];
      if (val && typeof val === "object" && !Array.isArray(val) && Object.keys(val).length > 12 && depth >= 1) {
        flattenRows(val, p, out, depth + 1);
      } else {
        flattenRows(val, p, out, depth + 1);
      }
    }
  }

  function detailTable(data, maxRows) {
    const rows = [];
    flattenRows(data, "", rows, 0);
    let html = '<table class="detail-table"><tbody>';
    for (const r of rows.slice(0, maxRows || 80)) {
      html += "<tr><th>" + esc(r.k) + "</th><td>" + esc(r.v) + "</td></tr>";
    }
    if (rows.length > (maxRows || 80)) {
      html += '<tr><th colspan="2">… ' + (rows.length - (maxRows || 80)) + " more rows</th></tr>";
    }
    html += "</tbody></table>";
    return html;
  }

  function weaponsTable(weapons, racks) {
    if (!weapons || !weapons.length) return "<p class='muted'>No weapons loaded</p>";
    const rackMeta = (racks && racks.racks) || {};
    let html = '<table class="weapons-table"><thead><tr>' +
      "<th>id</th><th>rack</th><th>label</th><th>entity</th><th>strike</th><th>offense</th><th>handler</th><th>targets</th><th>doctrine</th>" +
      "</tr></thead><tbody>";
    for (const w of weapons) {
      const rackLabel = (rackMeta[w.rack] || {}).label || w.rack;
      html += "<tr>" +
        "<td><code>" + esc(w.id) + "</code></td>" +
        "<td>" + esc(rackLabel) + "</td>" +
        "<td>" + esc(w.label) + "</td>" +
        "<td>" + esc(w.entity) + "</td>" +
        "<td>" + esc(w.strike) + "</td>" +
        "<td>" + esc(w.offense) + "</td>" +
        "<td>" + esc(w.handler || "—") + "</td>" +
        "<td>" + esc((w.targets || []).join(", ")) + "</td>" +
        "<td class='doc'>" + esc((w.doctrine || "").slice(0, 120)) + "</td>" +
        "</tr>";
    }
    html += "</tbody></table>";
    html += '<p class="muted">Total ' + weapons.length + " · racks " + Object.keys(rackMeta).length +
      " · socket: " + esc(((racks.socket_fit || {}).rule || "").slice(0, 100)) + "</p>";
    return html;
  }

  function threatMapTable(map) {
    if (!map) return "";
    let html = '<table class="detail-table compact"><thead><tr><th>threat</th><th>weapon</th></tr></thead><tbody>';
    for (const [t, w] of Object.entries(map).sort()) {
      html += "<tr><th>" + esc(t) + "</th><td><code>" + esc(w) + "</code></td></tr>";
    }
    return html + "</tbody></table>";
  }

  function modesTable(modes) {
    if (!modes || !modes.length) return "";
    let html = '<table class="detail-table"><thead><tr><th>id</th><th>label</th><th>detail</th></tr></thead><tbody>';
    for (const m of modes) {
      html += "<tr><th>" + esc(m.id || m) + "</th><td>" + esc(m.label) + "</td><td>" + esc(JSON.stringify(m).slice(0, 200)) + "</td></tr>";
    }
    return html + "</tbody></table>";
  }

  function renderSection(id, sec, meta) {
    const data = sec.data || {};
    const el = document.createElement("section");
    el.className = "ops-section";
    el.id = "sec-" + id;
    const badge = sec.ok ? "ok" : "err";
    let body = "";

    if (id === "weapons") {
      body += "<h3 class='block-title'>Full weapon rack (" + ((data.weapons || []).length) + ")</h3>";
      body += weaponsTable(data.weapons, data.racks);
      body += "<h3 class='block-title'>Threat → weapon map</h3>";
      body += threatMapTable(data.threat_weapon_map);
      body += "<h3 class='block-title'>Lie markers</h3><p class='mono'>" + esc((data.lie_markers || []).join(" · ")) + "</p>";
      body += "<h3 class='block-title'>Entity state</h3>";
      body += detailTable(data.state, 24);
      body += "<h3 class='block-title'>Endpoints</h3>";
      body += detailTable({ fire: data.fire_endpoint, weaponize: data.weaponize_endpoint }, 8);
      body += "<h3 class='block-title'>Doctrine</h3>";
      body += detailTable(data.doctrine, 40);
    } else if (id === "robotics") {
      body += "<h3 class='block-title'>Final modes</h3>" + modesTable(data.final_modes);
      body += "<h3 class='block-title'>Final eyeball (live)</h3>" + detailTable(data.final_eyeball, 50);
      body += "<h3 class='block-title'>Video / stream</h3>" + detailTable({ video: data.video, stream: data.stream, benchmark: data.benchmark }, 60);
      body += "<h3 class='block-title'>Rig · eye · contract</h3>" + detailTable({ rig: data.rig, eye: data.eye, contract: data.contract, presets: data.rig_presets }, 70);
      body += "<h3 class='block-title'>Arm endpoints</h3>" + detailTable(data.arm_endpoints, 10);
      body += "<h3 class='block-title'>Robotics doctrine</h3>" + detailTable(data.doctrine, 30);
    } else if (id === "ai") {
      body += "<h3 class='block-title'>Grok16 status</h3>" + detailTable(data.grok16, 40);
      body += "<h3 class='block-title'>Grok16 tune (war / patrol)</h3>" + detailTable({ war: data.grok16_tune_war, patrol: data.grok16_tune_patrol }, 20);
      body += "<h3 class='block-title'>Field compiler</h3>" + detailTable({ status: data.field_compiler, probe: data.compiler_probe }, 50);
      body += "<h3 class='block-title'>Neural assist</h3>" + detailTable({ neural: data.neural, verify: data.neural_verify }, 30);
      body += "<h3 class='block-title'>AI / robotics context</h3>" + detailTable({ grkmf: data.grkmf, ai: data.ai_context, robotics: data.robotics_context }, 40);
    } else if (id === "entity") {
      body += "<h3 class='block-title'>Twins status</h3>" + detailTable(data.twins, 50);
      body += "<h3 class='block-title'>Living (Vita)</h3>" + detailTable(data.living, 40);
      body += "<h3 class='block-title'>Truth (Veritas)</h3>" + detailTable(data.truth, 60);
      body += "<h3 class='block-title'>Recent forward ledger</h3>" + detailTable(data.recent_forward, 30);
      body += "<h3 class='block-title'>Sovereign + redundancy</h3>" + detailTable(data.sovereign_redundancy, 30);
    } else {
      body += detailTable(data, 120);
    }

    el.innerHTML =
      '<h2 class="sec-title">' + esc(meta.title) +
      ' <span class="sec-badge ' + badge + '">' + (sec.ok ? "OK" : "ERR") + " · " + sec.latency_ms + "ms</span></h2>" +
      '<p class="sec-sub">' + esc(meta.sub) + "</p>" +
      '<div class="sec-body">' + body + "</div>";
    return el;
  }

  function renderNav(priority) {
    const nav = $("opsNav");
    nav.textContent = "";
    for (const id of priority || []) {
      const m = SECTION_META[id] || { title: id };
      const a = document.createElement("a");
      a.href = "#sec-" + id;
      a.textContent = m.title.replace(/^\d+ · /, "");
      nav.appendChild(a);
    }
  }

  function renderMatrix(matrix) {
    const host = $("matrixGrid");
    host.textContent = "";
    if (!matrix || !matrix.cases) return;
    $("matrixSummary").textContent = matrix.passed + "/" + matrix.total + " (" + matrix.pass_pct + "%)";
    for (const c of matrix.cases) {
      const el = document.createElement("div");
      el.className = "mcase " + (c.ok ? "pass" : "fail");
      el.innerHTML = '<span class="id">' + esc(c.id) + "</span> " + esc(c.label) + " <strong>" + (c.ok ? "✓" : "✗") + "</strong>";
      host.appendChild(el);
    }
  }

  function updateHeader(ops) {
    const prod = ops.product || {};
    $("productTitle").textContent = (prod.name || "Final_Eye") + " Field Ops";
    $("productVer").textContent = (prod.product || "") + " v" + (prod.version || "?") + " · " + (prod.codename || "") + " · " + (ops.ts || "");
    const sum = ops.summary || {};
    const pct = sum.health_pct || 0;
    const h = $("healthPct");
    h.textContent = (sum.sections_ok || 0) + "/" + (sum.sections_total || 0) + " · " + pct + "%";
    h.className = "health" + (pct >= 90 ? "" : pct >= 75 ? " warn" : " fail");
    const hold = ops.copilot_hold || {};
    $("copilotIntegrity").textContent = "Co-Pilot " + (hold.integrity_pct || "—") + "% held";
    $("copilotSpeak").textContent = hold.speak || "—";
  }

  async function refresh() {
    try {
      const ops = await fetchJson("/api/ops/full");
      updateHeader(ops);
      renderNav(ops.priority);
      const main = $("opsMain");
      main.textContent = "";
      for (const id of ops.priority || []) {
        const sec = (ops.sections || {})[id];
        if (sec) main.appendChild(renderSection(id, sec, SECTION_META[id] || { title: id, sub: "" }));
      }
      if (ops.matrix) renderMatrix(ops.matrix);
      $("rawJson").textContent = JSON.stringify(ops, null, 2);
      $("footerTs").textContent = "Last poll " + new Date().toISOString() + " · /api/ops/full";
    } catch (e) {
      $("footerTs").textContent = "Error: " + e.message;
    }
  }

  $("btnRefresh").addEventListener("click", refresh);
  $("btnCopilotAsk").addEventListener("click", async () => {
    const q = ($("copilotQuery").value || "").trim() || "what holds weapons and trust together";
    try {
      const r = await fetchJson("/api/copilot/ask?q=" + encodeURIComponent(q));
      $("copilotAnswer").textContent = r.answer || "—";
    } catch (e) {
      $("copilotAnswer").textContent = e.message;
    }
  });
  $("copilotQuery").addEventListener("keydown", (e) => { if (e.key === "Enter") $("btnCopilotAsk").click(); });
  $("btnPoll").addEventListener("click", () => {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
      $("btnPoll").textContent = "Start poll";
    } else {
      pollTimer = setInterval(refresh, POLL_MS);
      $("btnPoll").textContent = "Stop poll";
    }
  });

  refresh();
  pollTimer = setInterval(refresh, POLL_MS);
})();