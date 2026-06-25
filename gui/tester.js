/* Final_Eye 1.0 internal tester — live factual panels */
(function () {
  "use strict";

  const POLL_MS = 2500;
  let lastFull = null;
  let pollTimer = null;

  const $ = (id) => document.getElementById(id);

  function labelClass(kind) {
    return kind || "implemented";
  }

  function fmt(v) {
    if (v === null || v === undefined) return "—";
    if (typeof v === "boolean") return v ? "yes" : "no";
    if (typeof v === "object") return JSON.stringify(v);
    return String(v);
  }

  function flatten(obj, prefix, out, depth) {
    if (depth > 4 || obj === null || obj === undefined) return;
    if (typeof obj !== "object" || Array.isArray(obj)) {
      out.push({ k: prefix, v: fmt(obj) });
      return;
    }
    if (obj.value !== undefined && obj.label) {
      out.push({ k: prefix, v: fmt(obj.value), kind: obj.label });
      return;
    }
    const keys = Object.keys(obj).slice(0, 40);
    for (const key of keys) {
      if (key.startsWith("_")) continue;
      const p = prefix ? prefix + "." + key : key;
      const val = obj[key];
      if (val && typeof val === "object" && !Array.isArray(val) && Object.keys(val).length > 6 && depth > 1) {
        out.push({ k: p, v: "[object]" });
      } else {
        flatten(val, p, out, depth + 1);
      }
    }
  }

  function renderCard(sub) {
    const card = document.createElement("div");
    card.className = "card";
    const ok = sub.ok;
    const h2 = document.createElement("h2");
    h2.innerHTML = sub.id + ' <span class="badge ' + (ok ? "ok" : "bad") + '">' +
      (ok ? "OK" : "ERR") + " · " + sub.latency_ms + "ms</span>";
    card.appendChild(h2);
    const body = document.createElement("div");
    body.className = "body";
    const rows = [];
    flatten(sub.data, "", rows, 0);
    for (const r of rows.slice(0, 48)) {
      const row = document.createElement("div");
      row.className = "row";
      const k = document.createElement("div");
      k.className = "k";
      k.textContent = r.k;
      const v = document.createElement("div");
      v.className = "v";
      if (r.kind) {
        const tag = document.createElement("span");
        tag.className = labelClass(r.kind);
        tag.style.fontSize = "0.58rem";
        tag.style.marginRight = "0.25rem";
        tag.textContent = r.kind.slice(0, 3);
        v.appendChild(tag);
      }
      v.appendChild(document.createTextNode(r.v));
      row.appendChild(k);
      row.appendChild(v);
      body.appendChild(row);
    }
    card.appendChild(body);
    return card;
  }

  function renderMatrix(matrix) {
    const host = $("matrixGrid");
    host.textContent = "";
    if (!matrix || !matrix.cases) return;
    $("matrixSummary").textContent =
      matrix.passed + "/" + matrix.total + " passed (" + matrix.pass_pct + "%)";
    for (const c of matrix.cases) {
      const el = document.createElement("div");
      el.className = "mcase " + (c.ok ? "pass" : "fail");
      el.innerHTML =
        '<div><div class="id">' + c.id + " · " + c.kind + "</div>" +
        '<div class="lbl">' + c.label + "</div></div>" +
        '<div>' + (c.ok ? "✓" : "✗") + "</div>";
      host.appendChild(el);
    }
  }

  function updateHeader(full) {
    const snap = full.snapshot || {};
    const prod = snap.product || {};
    const sum = snap.summary || {};
    $("productTitle").textContent = (prod.name || "Final_Eye") + " Internal Tester";
    $("productVer").textContent =
      (prod.product || "") + " v" + (prod.version || "?") +
      " · " + (prod.codename || "") + " · " + (snap.ts || "");
    const pct = sum.health_pct || 0;
    const h = $("healthPct");
    h.textContent = pct + "%";
    h.className = "health" + (pct >= 90 ? "" : pct >= 70 ? " warn" : " fail");
    $("readyFlag").textContent = full.release_ready ? "RELEASE READY" : "NOT READY";
    $("readyFlag").style.color = full.release_ready ? "var(--ok)" : "var(--fail)";
  }

  async function fetchJson(url) {
    const r = await fetch(url, { cache: "no-store" });
    return r.json();
  }

  async function refresh(runMatrix) {
    try {
      const url = "/api/tester/full" + (runMatrix ? "?matrix=1" : "");
      const full = await fetchJson(url);
      lastFull = full;
      updateHeader(full);
      const grid = $("subGrid");
      grid.textContent = "";
      const subs = (full.snapshot && full.snapshot.subsystems) || [];
      for (const s of subs) grid.appendChild(renderCard(s));
      if (full.matrix) renderMatrix(full.matrix);
      $("rawJson").textContent = JSON.stringify(full, null, 2);
      $("footerTs").textContent = "Last poll: " + new Date().toISOString();
    } catch (e) {
      $("footerTs").textContent = "Poll error: " + e.message;
    }
  }

  function startPoll() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => refresh(false), POLL_MS);
  }

  $("btnRefresh").addEventListener("click", () => refresh(true));
  $("btnMatrix").addEventListener("click", async () => {
    const m = await fetchJson("/api/tester/matrix");
    renderMatrix(m);
  });
  $("btnPoll").addEventListener("click", () => {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
      $("btnPoll").textContent = "Start poll";
    } else {
      startPoll();
      $("btnPoll").textContent = "Stop poll";
    }
  });

  refresh(true);
  startPoll();
  $("btnPoll").textContent = "Stop poll";
})();