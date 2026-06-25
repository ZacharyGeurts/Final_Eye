/**
 * ZOCR HUD — closed manifest module bar.
 * No innerHTML from API payloads. No runtime plugins. Whitelist renderers only.
 */
(function () {
  'use strict';

  const GAMUT_MIN = 300;
  const GAMUT_MAX = 800;

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null && text !== '') node.textContent = String(text);
    return node;
  }

  function meterLine(label, value) {
    const line = el('div', 'hud-meter-line');
    line.appendChild(document.createTextNode(label + ' '));
    const span = el('span', null, value == null ? '—' : value);
    line.appendChild(span);
    return line;
  }

  function tileData(tile) {
    if (!tile || !tile.ok) return null;
    return tile.data || null;
  }

  const TILE_FMT = {
    spectrum(d) {
      const frag = document.createDocumentFragment();
      const rng = d.range_nm || [];
      const nm = rng.length >= 2 ? rng[0] + '–' + rng[1] + 'nm' : '—';
      frag.appendChild(meterLine('profile', (d.label || d.profile) + ' · ' + nm));
      frag.appendChild(meterLine('class', d.class || '—'));
      frag.appendChild(meterLine('engine', d.engine || 'cone_v2'));
      if (d.teach) {
        const t = el('div', 'hud-meter-line', d.teach);
        frag.appendChild(t);
      }
      return frag;
    },
    stream_meter(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('format', d.format || 'ZOCRSM1'));
      frag.appendChild(meterLine('run', d.running ? 'yes' : 'no'));
      frag.appendChild(meterLine('fps', d.fps));
      frag.appendChild(meterLine('fabric', (d.fabric_nm_per_px || '—') + 'nm/px'));
      return frag;
    },
    stereo_depth(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('mode', d.mode));
      frag.appendChild(meterLine('eyes', d.eye_count));
      frag.appendChild(meterLine('stereo', d.stereo ? 'on' : 'off'));
      return frag;
    },
    threat_overlay(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('confidence', d.confidence));
      frag.appendChild(meterLine('threats', d.threats_total));
      frag.appendChild(meterLine('failovers', d.failovers_total));
      return frag;
    },
    sovereign_clock(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('verdict', d.verdict));
      frag.appendChild(meterLine('mono', d.sealed_mono_ns));
      return frag;
    },
    trust_woven(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('mesh', d.mesh_ok ? 'woven' : 'partial'));
      frag.appendChild(meterLine('paths', d.woven));
      frag.appendChild(meterLine('peers', d.peers));
      return frag;
    },
    twin_entity(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('Vita', d.vita_live ? 'live' : '—'));
      frag.appendChild(meterLine('Veritas', d.veritas_forward ? 'forward' : '—'));
      if (d.speak) frag.appendChild(el('div', 'hud-meter-line', d.speak));
      return frag;
    },
    final_mode(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('mode', d.mode));
      frag.appendChild(meterLine('voice', d.voice));
      if (d.speak) frag.appendChild(el('div', 'hud-meter-line', d.speak));
      return frag;
    },
    neural_assist(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('network', d.network));
      frag.appendChild(meterLine('seal', d.seal_ok ? 'OK' : '—'));
      return frag;
    },
    pattern_weave(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('enabled', d.enabled ? 'yes' : 'no'));
      frag.appendChild(meterLine('scans', d.scans));
      frag.appendChild(meterLine('foreign', d.foreign));
      return frag;
    },
    kill_gate(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('whole', d.whole !== false ? 'armed' : 'KILLED'));
      frag.appendChild(meterLine('eyes', d.eyes ? 'protected' : 'off'));
      return frag;
    },
    offense_streak(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('strikes', d.strikes));
      frag.appendChild(meterLine('streak', d.streak));
      frag.appendChild(meterLine('preempt', d.preempt ? 'armed' : 'idle'));
      return frag;
    },
    capture_cascade(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('source', d.last_source));
      frag.appendChild(meterLine('vault', d.last_good ? 'armed' : 'empty'));
      return frag;
    },
    ocr_hud(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('last', d.last_action));
      if (d.snippet) frag.appendChild(el('div', 'hud-meter-line', d.snippet));
      return frag;
    },
    contract_budget(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('posture', d.posture));
      return frag;
    },
    entity_weapons(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('rack', d.count));
      if (d.ids && d.ids.length) {
        frag.appendChild(el('div', 'hud-meter-line', d.ids.join(' · ')));
      }
      return frag;
    },
    vigilance_patrol(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('running', d.running ? 'yes' : 'no'));
      frag.appendChild(meterLine('checks', d.checks));
      frag.appendChild(meterLine('alerts', d.alerts));
      return frag;
    },
    video_tune(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('fps', d.fps));
      frag.appendChild(meterLine('size', (d.width || '—') + '×' + (d.height || '—')));
      return frag;
    },
    look_radar(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('source', d.last_source));
      frag.appendChild(meterLine('confidence', d.vision_confidence));
      return frag;
    },
    field_compiler(d) {
      const frag = document.createDocumentFragment();
      frag.appendChild(meterLine('Grok16', (d.grok16 || '—') + ' · ' + (d.profile || 'field_opt')));
      frag.appendChild(meterLine('g16', d.g16_ready ? 'ready' : 'probe'));
      frag.appendChild(meterLine('forge', d.forge_stage));
      frag.appendChild(meterLine('rtx', d.rtx_ready ? 'ready' : 'build'));
      return frag;
    },
  };

  function nmColor(lo, hi) {
    const mid = (lo + hi) / 2;
    if (mid < 450) return '#6b8cff';
    if (mid < 550) return '#4ade80';
    if (mid < 620) return '#fbbf24';
    return '#f87171';
  }

  function renderSpectrumGamut(analysis) {
    const wrap = el('div', 'hud-spectrum');
    const data = (analysis && analysis.analysis) || analysis || {};
    const gamut = data.gamut || [];
    const bar = el('div', 'hud-gamut');
    gamut.forEach(function (g) {
      const rng = g.range_nm || [];
      if (rng.length < 2) return;
      const lo = Math.max(GAMUT_MIN, Number(rng[0]) || GAMUT_MIN);
      const hi = Math.min(GAMUT_MAX, Number(rng[1]) || GAMUT_MAX);
      const span = Math.max(1, hi - lo);
      const seg = el('div', 'hud-gamut-seg' + (g.active ? ' active' : ''));
      seg.style.flex = String(span);
      seg.style.background = nmColor(lo, hi);
      seg.title = (g.label || g.id || '') + ' ' + lo + '–' + hi + 'nm';
      bar.appendChild(seg);
    });
    wrap.appendChild(bar);
    const labels = el('div', 'hud-gamut-labels');
    if (data.summary) {
      labels.appendChild(el('span', null, data.summary));
    } else {
      const rng = data.range_nm || [];
      const nm = rng.length >= 2 ? rng[0] + '–' + rng[1] + 'nm' : '—';
      labels.appendChild(el('span', null, (data.label || data.profile || 'spectrum') + ' · ' + nm));
    }
    wrap.appendChild(labels);
    return wrap;
  }

  function renderFocus(posture, tiles, spectrum) {
    const focusId = posture.focus;
    const mods = posture.modules || [];
    const mod = mods.find(function (m) { return m.id === focusId; }) || mods.find(function (m) { return m.active; });
    const title = el('div', 'hud-focus-title', mod ? mod.label + ' · ' + mod.id : 'HUD focus');
    const body = el('div', 'hud-focus-body');

    if (focusId === 'spectrum' || (!focusId && (tiles.spectrum || spectrum))) {
      const specTile = tiles.spectrum;
      const fmt = TILE_FMT.spectrum;
      const d = tileData(specTile) || ((spectrum && spectrum.analysis) || {});
      if (fmt && d) body.appendChild(fmt(d));
      body.appendChild(renderSpectrumGamut(spectrum || { analysis: d }));
    } else if (mod && TILE_FMT[mod.id]) {
      const d = tileData(tiles[mod.id]);
      if (d) body.appendChild(TILE_FMT[mod.id](d));
      else body.appendChild(el('div', 'hud-meter-line', mod.describe || '—'));
    } else if (mod) {
      body.appendChild(el('div', 'hud-meter-line', mod.describe || '—'));
    } else {
      body.appendChild(el('div', 'hud-meter-line', 'No active HUD modules'));
    }

    return { title: title, body: body };
  }

  async function hudRequest(action, module) {
    const r = await fetch('/api/hud/request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: action, module: module }),
    });
    return r.json();
  }

  function renderBar(status) {
    const bar = document.getElementById('hudBar');
    if (!bar) return;

    const posture = status.posture || {};
    const modules = posture.modules || [];
    const maxActive = posture.max_active || 8;
    const activeCount = modules.filter(function (m) { return m.active; }).length;

    let rule = bar.querySelector('.hud-rule');
    if (!rule) {
      rule = el('div', 'hud-rule');
      bar.appendChild(rule);
    }
    rule.textContent = posture.rule || 'Closed manifest only — no runtime modules';

    let row = bar.querySelector('.hud-row');
    if (!row) {
      row = el('div', 'hud-row');
      bar.appendChild(row);
    }
    row.replaceChildren();

    const switches = el('div', 'hud-switches');
    modules.forEach(function (m) {
      const btn = el('button', 'hud-chip' + (m.active ? ' on' : '') + (m.focus ? ' focus' : ''), m.label);
      btn.type = 'button';
      btn.dataset.module = m.id;
      btn.title = m.describe || m.id;
      btn.onclick = async function () {
        const res = await hudRequest('toggle', m.id);
        if (res.ok) renderBar(await fetchStatus());
        else btn.disabled = true;
      };
      btn.oncontextmenu = function (ev) {
        ev.preventDefault();
        hudRequest('focus', m.id).then(function (res) {
          if (res.ok) renderBar({ posture: res.posture, tiles: status.tiles || {}, spectrum: status.spectrum });
        });
        return false;
      };
      switches.appendChild(btn);
    });
    row.appendChild(switches);

    const focusBox = el('div', 'hud-focus');
    const focusParts = renderFocus(posture, status.tiles || {}, status.spectrum);
    focusBox.appendChild(focusParts.title);
    focusBox.appendChild(focusParts.body);
    row.appendChild(focusBox);

    const actions = el('div', 'hud-actions');
    const analyzeBtn = el('button', null, 'Spectrum analyze');
    analyzeBtn.type = 'button';
    analyzeBtn.onclick = async function () {
      const r = await fetch('/api/hud/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ module: 'spectrum' }),
      });
      const d = await r.json();
      if (d.ok) {
        const st = await fetchStatus();
        st.spectrum = d;
        renderBar(st);
      }
    };
    actions.appendChild(analyzeBtn);

    const count = el('div', 'hud-count', activeCount + '/' + maxActive + ' active');
    actions.appendChild(count);
    row.appendChild(actions);
  }

  async function fetchStatus() {
    const res = await fetch('/api/hud/status', { cache: 'no-store' });
    if (!res.ok) throw new Error('hud offline');
    return res.json();
  }

  async function pollHud() {
    try {
      const st = await fetchStatus();
      renderBar(st);
    } catch (_e) {
      const bar = document.getElementById('hudBar');
      if (bar && !bar.querySelector('.hud-rule')) {
        bar.appendChild(el('div', 'hud-rule', 'HUD offline'));
      }
    }
  }

  window.ZOCRHud = { poll: pollHud, request: hudRequest, render: renderBar };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      pollHud();
      setInterval(pollHud, 4000);
    });
  } else {
    pollHud();
    setInterval(pollHud, 4000);
  }
})();