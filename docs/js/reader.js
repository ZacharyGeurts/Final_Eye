/**
 * Field Primer — immersive reader with vanilla paper preset and custom ink.
 */
(function () {
  "use strict";

  const STORAGE_KEY = "final-eye-reader-v1";

  const PRESETS = {
    vanilla: {
      name: "Vanilla",
      paper: "#f7f2e8",
      ink: "#2e261c",
      muted: "#6b5e4f",
      accent: "#8b6914",
      codeBg: "#ede6d6",
      codeInk: "#5c4a32",
      warmth: 18,
      texture: 1,
      font: "literata",
      size: 1.125,
      leading: 1.85,
      width: "42rem",
    },
    parchment: {
      name: "Parchment",
      paper: "#f3ead8",
      ink: "#3a3228",
      muted: "#7a6e5c",
      accent: "#7a5c1e",
      codeBg: "#e6dcc8",
      codeInk: "#4a4030",
      warmth: 10,
      texture: 1,
      font: "lora",
      size: 1.1,
      leading: 1.8,
      width: "40rem",
    },
    sepia: {
      name: "Sepia Evening",
      paper: "#e8dcc4",
      ink: "#2a2218",
      muted: "#5c5040",
      accent: "#6b4423",
      codeBg: "#ddd0b8",
      codeInk: "#3d3020",
      warmth: 22,
      texture: 1,
      font: "literata",
      size: 1.15,
      leading: 1.9,
      width: "44rem",
    },
    midnight: {
      name: "Midnight Study",
      paper: "#1a2234",
      ink: "#dce8f8",
      muted: "#8aa4c8",
      accent: "#38bdf8",
      codeBg: "#0f1a2e",
      codeInk: "#f0d060",
      warmth: 0,
      texture: 0.4,
      font: "lora",
      size: 1.1,
      leading: 1.75,
      width: "42rem",
    },
    field: {
      name: "Field Dark",
      paper: "#0a1220",
      ink: "#e8f2ff",
      muted: "#8aa4c8",
      accent: "#38bdf8",
      codeBg: "#0f1a2e",
      codeInk: "#f0d060",
      warmth: 0,
      texture: 0.2,
      font: "system",
      size: 1.0625,
      leading: 1.7,
      width: "42rem",
    },
    classroom: {
      name: "Classroom",
      paper: "#fffef9",
      ink: "#1a1a1a",
      muted: "#4a4a4a",
      accent: "#1d4ed8",
      codeBg: "#f4f4f0",
      codeInk: "#1e3a5f",
      warmth: 4,
      texture: 0.15,
      font: "charter",
      size: 1.125,
      leading: 1.9,
      width: "42rem",
    },
  };

  const FONTS = {
    literata: '"Literata", "Palatino Linotype", "Book Antiqua", Georgia, serif',
    lora: '"Lora", Georgia, "Times New Roman", serif',
    georgia: 'Georgia, "Times New Roman", serif',
    charter: 'Charter, "Bitstream Charter", Georgia, serif',
    system: '"Segoe UI", system-ui, -apple-system, sans-serif',
  };

  const WIDTHS = {
    narrow: "34rem",
    medium: "42rem",
    wide: "52rem",
  };

  function isMobile() {
    return window.matchMedia("(max-width: 768px)").matches;
  }

  function isTablet() {
    return window.matchMedia("(min-width: 769px) and (max-width: 1024px)").matches;
  }

  function hexToRgb(hex) {
    const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex || "");
    if (!m) return { r: 46, g: 38, b: 28 };
    return { r: parseInt(m[1], 16), g: parseInt(m[2], 16), b: parseInt(m[3], 16) };
  }

  function rgbToHex(r, g, b) {
    const clamp = (n) => Math.max(0, Math.min(255, Math.round(n)));
    return (
      "#" +
      [clamp(r), clamp(g), clamp(b)]
        .map((x) => x.toString(16).padStart(2, "0"))
        .join("")
    );
  }

  function mixHex(a, b, t) {
    const c = hexToRgb(a);
    const d = hexToRgb(b);
    return rgbToHex(c.r + (d.r - c.r) * t, c.g + (d.g - c.g) * t, c.b + (d.b - c.b) * t);
  }

  function paperIsDark(paper) {
    const { r, g, b } = hexToRgb(paper);
    const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return lum < 0.45;
  }

  function deriveCompanionColors(paper, ink) {
    const dark = paperIsDark(paper);
    return {
      muted: mixHex(ink, paper, dark ? 0.42 : 0.38),
      codeBg: mixHex(paper, ink, dark ? 0.12 : 0.07),
      codeInk: mixHex(ink, paper, dark ? 0.18 : 0.12),
    };
  }

  function rgbaFromHex(hex, alpha) {
    const { r, g, b } = hexToRgb(hex);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function mobileDefaults() {
    const base = { ...PRESETS.vanilla, preset: "vanilla" };
    if (isMobile()) {
      base.size = 1.05;
      base.leading = 1.8;
      base.width = WIDTHS.narrow;
    } else if (isTablet()) {
      base.width = WIDTHS.medium;
    }
    return base;
  }

  function normalizeSettings(raw) {
    const base = { ...PRESETS.vanilla, ...raw };
    base.mutedManual = Boolean(raw.mutedManual);
    base.codeBgManual = Boolean(raw.codeBgManual);
    base.codeInkManual = Boolean(raw.codeInkManual);
    return base;
  }

  function loadSettings() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return normalizeSettings(JSON.parse(raw));
    } catch (_) {
      /* ignore */
    }
    return normalizeSettings(mobileDefaults());
  }

  function saveSettings(s) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
    } catch (_) {
      /* ignore */
    }
  }

  function applySettings(s, root) {
    const r = root || document.documentElement;
    const themeMeta = document.querySelector('meta[name="theme-color"]');
    if (themeMeta && document.body.classList.contains("reader-active")) {
      themeMeta.setAttribute("content", s.paper);
    }
    r.style.setProperty("--reader-paper", s.paper);
    r.style.setProperty("--reader-ink", s.ink);
    r.style.setProperty("--reader-muted", s.muted);
    r.style.setProperty("--reader-accent", s.accent);
    r.style.setProperty("--reader-code-bg", s.codeBg);
    r.style.setProperty("--reader-code-ink", s.codeInk);
    r.style.setProperty("--reader-font", FONTS[s.font] || FONTS.literata);
    r.style.setProperty("--reader-size", `${s.size}rem`);
    r.style.setProperty("--reader-leading", String(s.leading));
    r.style.setProperty("--reader-width", s.width);
    r.style.setProperty("--reader-warmth", String(s.warmth));
    r.style.setProperty("--reader-texture", String(s.texture));
    r.style.setProperty("--reader-border", rgbaFromHex(s.ink, paperIsDark(s.paper) ? 0.22 : 0.14));
  }

  function applyDerivedColors(settings, keys) {
    const derived = deriveCompanionColors(settings.paper, settings.ink);
    if (!settings.mutedManual || keys.has("paper") || keys.has("ink")) {
      settings.muted = derived.muted;
      if (keys.has("paper") || keys.has("ink")) settings.mutedManual = false;
    }
    if (!settings.codeBgManual || keys.has("paper") || keys.has("ink")) {
      settings.codeBg = derived.codeBg;
      if (keys.has("paper") || keys.has("ink")) settings.codeBgManual = false;
    }
    if (!settings.codeInkManual || keys.has("paper") || keys.has("ink")) {
      settings.codeInk = derived.codeInk;
      if (keys.has("paper") || keys.has("ink")) settings.codeInkManual = false;
    }
  }

  function wantsReader() {
    const params = new URLSearchParams(window.location.search);
    return params.get("reader") === "1" || window.location.hash === "#read";
  }

  function readerHref(href) {
    if (!href || href.startsWith("#")) return href;
    try {
      const url = new URL(href, window.location.href);
      url.searchParams.set("reader", "1");
      return url.pathname + url.search + url.hash;
    } catch (_) {
      return href;
    }
  }

  function initChapterReader() {
    const main = document.querySelector("main.chapter-main");
    if (!main) return;

    const heroTitle =
      document.querySelector(".chapter-hero h1")?.textContent?.trim() ||
      document.querySelector(".creditor-hero-text h1")?.textContent?.trim() ||
      document.title;
    const prevLink = main.querySelector(".chapter-nav:not(.bottom) a.btn.secondary");
    const nextLink = main.querySelector(".chapter-nav:not(.bottom) a.btn:not(.secondary)");
    const contentClone = main.cloneNode(true);

    contentClone.querySelectorAll(".chapter-nav").forEach((el) => el.remove());

    let settings = loadSettings();
    let settingsOpen = false;

    const launch = document.createElement("button");
    launch.type = "button";
    launch.className = "reader-launch";
    launch.setAttribute("aria-label", "Open immersive reader");
    launch.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5z"/></svg><span class="label-full"> Read</span>';

    const shell = document.createElement("div");
    shell.className = "reader-shell";
    shell.setAttribute("role", "dialog");
    shell.setAttribute("aria-label", "Immersive reader");
    shell.innerHTML = `
      <div class="reader-toolbar">
        <div class="reader-toolbar-left">
          <button type="button" class="reader-btn" data-action="exit" aria-label="Exit reader">✕ Exit</button>
          <span class="reader-title">${escapeHtml(heroTitle)}</span>
        </div>
        <div class="reader-toolbar-right">
          ${prevLink ? `<a class="reader-btn" href="${readerHref(prevLink.getAttribute("href"))}">${prevLink.textContent.trim()}</a>` : ""}
          ${nextLink ? `<a class="reader-btn primary" href="${readerHref(nextLink.getAttribute("href"))}">${nextLink.textContent.trim()}</a>` : ""}
          <button type="button" class="reader-btn" data-action="settings" aria-label="Reader settings">⚙ Paper &amp; ink</button>
        </div>
      </div>
      <div class="reader-progress"><div class="reader-progress-bar"></div></div>
      <div class="reader-viewport">
        <div class="reader-page">
          <article class="reader-paper">
            <div class="reader-content"></div>
          </article>
        </div>
      </div>
    `;

    const settingsOverlay = document.createElement("div");
    settingsOverlay.className = "reader-settings-overlay";

    const settingsPanel = document.createElement("aside");
    settingsPanel.className = "reader-settings";
    settingsPanel.innerHTML = buildSettingsHtml();

    document.body.appendChild(launch);
    document.body.appendChild(shell);
    document.body.appendChild(settingsOverlay);
    document.body.appendChild(settingsPanel);

    const viewport = shell.querySelector(".reader-viewport");
    const progressBar = shell.querySelector(".reader-progress-bar");
    const readerContent = shell.querySelector(".reader-content");
    readerContent.appendChild(contentClone);

    applySettings(settings, shell);

    let scrollY = 0;

    function openReader() {
      scrollY = window.scrollY;
      document.body.classList.add("reader-active");
      document.body.style.top = `-${scrollY}px`;
      applySettings(settings, shell);
      syncSettingsUi();
      viewport.scrollTop = 0;
      updateProgress();
      launch.setAttribute("aria-expanded", "true");
    }

    function closeReader() {
      document.body.classList.remove("reader-active");
      document.body.style.top = "";
      window.scrollTo(0, scrollY);
      const themeMeta = document.querySelector('meta[name="theme-color"]');
      if (themeMeta) themeMeta.setAttribute("content", "#040810");
      closeSettings();
      launch.setAttribute("aria-expanded", "false");
    }

    function closeSettings() {
      settingsOpen = false;
      settingsPanel.classList.remove("open");
      settingsOverlay.classList.remove("open");
    }

    function openSettings() {
      settingsOpen = true;
      settingsPanel.classList.add("open");
      settingsOverlay.classList.add("open");
      syncSettingsUi();
    }

    function updateProgress() {
      const max = viewport.scrollHeight - viewport.clientHeight;
      const pct = max > 0 ? (viewport.scrollTop / max) * 100 : 0;
      progressBar.style.width = `${pct}%`;
    }

    function setPreset(name) {
      if (!PRESETS[name]) return;
      settings = normalizeSettings({ ...PRESETS[name], preset: name });
      applySettings(settings, shell);
      saveSettings(settings);
      syncSettingsUi();
      updateHomePreview();
    }

    function resetVanilla() {
      setPreset("vanilla");
    }

    function syncSettingsUi() {
      settingsPanel.querySelectorAll(".reader-preset").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.preset === settings.preset);
      });
      setVal("paper", settings.paper);
      setVal("ink", settings.ink);
      setVal("accent", settings.accent);
      setVal("font", settings.font);
      setVal("size", settings.size);
      setVal("leading", settings.leading);
      setVal("width", widthKey(settings.width));
      setVal("texture", settings.texture);
      setVal("warmth", settings.warmth);
      setVal("muted", settings.muted);
      setVal("codeBg", settings.codeBg);
      setVal("codeInk", settings.codeInk);
    }

    function setVal(id, v) {
      const el = settingsPanel.querySelector(`[data-setting="${id}"]`);
      if (el) el.value = v;
    }

    function widthKey(w) {
      for (const [k, v] of Object.entries(WIDTHS)) {
        if (v === w) return k;
      }
      return "medium";
    }

    function bindSettings() {
      settingsPanel.querySelectorAll(".reader-preset").forEach((btn) => {
        btn.addEventListener("click", () => setPreset(btn.dataset.preset));
      });

      settingsPanel.querySelectorAll("[data-setting]").forEach((el) => {
        el.addEventListener("input", () => {
          const key = el.dataset.setting;
          let val = el.value;
          if (key === "size" || key === "leading" || key === "texture" || key === "warmth") {
            val = parseFloat(val);
          }
          const changed = new Set([key]);
          if (key === "width") {
            settings.width = WIDTHS[val] || WIDTHS.medium;
          } else {
            settings[key] = val;
          }
          if (key === "muted") settings.mutedManual = true;
          if (key === "codeBg") settings.codeBgManual = true;
          if (key === "codeInk") settings.codeInkManual = true;
          if (key === "paper" || key === "ink") {
            applyDerivedColors(settings, changed);
          }
          settings.preset = "custom";
          applySettings(settings, shell);
          saveSettings(settings);
          syncSettingsUi();
          updateHomePreview();
          settingsPanel.querySelectorAll(".reader-preset").forEach((b) => b.classList.remove("active"));
        });
      });

      settingsPanel.querySelector('[data-action="reset-vanilla"]')?.addEventListener("click", resetVanilla);
      settingsPanel.querySelector(".reader-settings-close")?.addEventListener("click", closeSettings);
    }

    launch.addEventListener("click", openReader);
    shell.querySelector('[data-action="exit"]')?.addEventListener("click", closeReader);
    shell.querySelector('[data-action="settings"]')?.addEventListener("click", openSettings);
    settingsOverlay.addEventListener("click", closeSettings);
    viewport.addEventListener("scroll", updateProgress, { passive: true });

    let touchStartY = 0;
    settingsPanel.addEventListener(
      "touchstart",
      (e) => {
        touchStartY = e.touches[0].clientY;
      },
      { passive: true }
    );
    settingsPanel.addEventListener(
      "touchend",
      (e) => {
        if (!settingsOpen || !isMobile()) return;
        const dy = e.changedTouches[0].clientY - touchStartY;
        if (dy > 80) closeSettings();
      },
      { passive: true }
    );

    document.addEventListener("keydown", (e) => {
      if (!document.body.classList.contains("reader-active")) return;
      if (e.key === "Escape") {
        if (settingsOpen) closeSettings();
        else closeReader();
      }
      if (e.key === "=" || e.key === "+") {
        settings.size = Math.min(1.5, settings.size + 0.05);
        applySettings(settings, shell);
        saveSettings(settings);
        syncSettingsUi();
      }
      if (e.key === "-") {
        settings.size = Math.max(0.9, settings.size - 0.05);
        applySettings(settings, shell);
        saveSettings(settings);
        syncSettingsUi();
      }
    });

    bindSettings();
    syncSettingsUi();
    updateHomePreview();

    if (wantsReader()) {
      requestAnimationFrame(() => openReader());
    }
  }

  function boot() {
    initHomeReaderRoom();
    initChapterReader();
  }

  function buildSettingsHtml() {
    const presetBtns = Object.entries(PRESETS)
      .map(
        ([id, p]) =>
          `<button type="button" class="reader-preset ${id}" data-preset="${id}"><span class="reader-preset-swatch"></span>${p.name}</button>`
      )
      .join("");

    return `
      <button type="button" class="reader-btn reader-settings-close" aria-label="Close settings">✕</button>
      <p class="settings-eyebrow">Paper &amp; ink</p>
      <h3>Reading room</h3>
      <p class="reader-vanilla-note">Vanilla is the default — warm cream paper, brown ink, soft grain. Close your eyes; you can almost smell it.</p>
      <section>
        <label>Presets</label>
        <div class="reader-preset-grid">${presetBtns}</div>
      </section>
      <section>
        <label for="reader-paper">Paper</label>
        <input type="color" id="reader-paper" data-setting="paper" value="#f7f2e8" />
        <label for="reader-ink" style="margin-top:0.75rem">Ink</label>
        <input type="color" id="reader-ink" data-setting="ink" value="#2e261c" />
        <label for="reader-accent" style="margin-top:0.75rem">Accent (links &amp; headings)</label>
        <input type="color" id="reader-accent" data-setting="accent" value="#8b6914" />
      </section>
      <section>
        <label>Advanced ink</label>
        <p class="reader-advanced-note">Muted and code colors auto-match paper and ink until you change them here.</p>
        <label for="reader-muted" style="margin-top:0.5rem">Muted text</label>
        <input type="color" id="reader-muted" data-setting="muted" value="#6b5e4f" />
        <label for="reader-code-bg" style="margin-top:0.75rem">Code block background</label>
        <input type="color" id="reader-code-bg" data-setting="codeBg" value="#ede6d6" />
        <label for="reader-code-ink" style="margin-top:0.75rem">Code block text</label>
        <input type="color" id="reader-code-ink" data-setting="codeInk" value="#5c4a32" />
      </section>
      <section>
        <label for="reader-font">Typeface</label>
        <select id="reader-font" data-setting="font">
          <option value="literata">Literata — book serif</option>
          <option value="lora">Lora — gentle serif</option>
          <option value="georgia">Georgia — classic</option>
          <option value="charter">Charter — textbook</option>
          <option value="system">System sans</option>
        </select>
        <label for="reader-size" style="margin-top:0.75rem">Size</label>
        <input type="range" id="reader-size" data-setting="size" min="0.9" max="1.5" step="0.025" />
        <label for="reader-leading" style="margin-top:0.75rem">Line height</label>
        <input type="range" id="reader-leading" data-setting="leading" min="1.4" max="2.2" step="0.05" />
        <label for="reader-width" style="margin-top:0.75rem">Column width</label>
        <select id="reader-width" data-setting="width">
          <option value="narrow">Narrow — focused</option>
          <option value="medium">Medium — textbook</option>
          <option value="wide">Wide — reference</option>
        </select>
      </section>
      <section>
        <label for="reader-texture">Paper grain</label>
        <input type="range" id="reader-texture" data-setting="texture" min="0" max="1" step="0.1" />
        <label for="reader-warmth" style="margin-top:0.75rem">Vanilla warmth</label>
        <input type="range" id="reader-warmth" data-setting="warmth" min="0" max="30" step="1" />
      </section>
      <section>
        <button type="button" class="reader-btn reader-reset-vanilla" data-action="reset-vanilla">↺ Reset to Vanilla</button>
      </section>
    `;
  }

  function updateHomePreview() {
    const preview = document.getElementById("reader-room-preview");
    if (!preview) return;
    const s = loadSettings();
    preview.style.setProperty("--preview-paper", s.paper);
    preview.style.setProperty("--preview-ink", s.ink);
    preview.style.setProperty("--preview-accent", s.accent);
    preview.style.setProperty("--preview-muted", s.muted);
    preview.style.setProperty("--preview-code-bg", s.codeBg);
    preview.style.setProperty("--preview-code-ink", s.codeInk);
    preview.style.setProperty("--preview-texture", String(s.texture));
    const label = preview.querySelector(".reader-preview-label");
    if (label) {
      label.textContent =
        s.preset && s.preset !== "custom" && PRESETS[s.preset]
          ? PRESETS[s.preset].name
          : "Custom";
    }
  }

  function initHomeReaderRoom() {
    const room = document.getElementById("reader-room");
    if (!room) return;
    updateHomePreview();
    window.addEventListener("storage", (e) => {
      if (e.key === STORAGE_KEY) updateHomePreview();
    });
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();