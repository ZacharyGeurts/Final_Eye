#!/usr/bin/env python3
"""Build Final_Eye GitHub Pages textbook chapters from manuscript blocks."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CHAPTERS = DOCS / "chapters"


def _version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _version_short() -> str:
    v = _version()
    parts = v.split(".")
    return f"v{parts[0]}.{parts[1]}" if len(parts) >= 2 else f"v{v}"


def _shell(
    *,
    num: int,
    slug: str,
    title: str,
    subtitle: str,
    accent: str,
    hero_img: str,
    prev_href: str | None,
    prev_label: str,
    next_href: str | None,
    next_label: str,
    objectives: list[str],
    toc: list[tuple[str, str]],
    on_the_way: str,
    journey: list[str],
    body: str,
    questions: list[str],
) -> str:
    nav_prev = f'<a class="btn secondary" href="{prev_href}">{prev_label}</a>' if prev_href else '<span></span>'
    nav_next = f'<a class="btn" href="{next_href}">{next_label}</a>' if next_href else '<span></span>'
    toc_html = "".join(f'<li><a href="#{aid}">{label}</a></li>' for aid, label in toc)
    obj_html = "".join(f"<li>{o}</li>" for o in objectives)
    journey_html = "".join(f"<li>{j}</li>" for j in journey)
    q_html = "".join(f"<li>{q}</li>" for q in questions)
    img = f"../assets/images/chapters/{hero_img}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>{num:02d} — {title} · The Final Eyeball</title>
  <meta name="description" content="Chapter {num}: {title}. Final_Eye {_version_short()} sovereign vision textbook." />
  <link rel="canonical" href="https://zacharygeurts.github.io/Final_Eye/chapters/{slug}" />
  <meta name="theme-color" content="#05070a" />
  <meta property="og:title" content="{num:02d} — {title}" />
  <meta property="og:image" content="https://zacharygeurts.github.io/Final_Eye/assets/images/chapters/{hero_img}" />
  <link rel="stylesheet" href="../css/final-eye.css" />
  <link rel="stylesheet" href="../css/chapters.css" />
  <link rel="stylesheet" href="../css/reader.css" />
</head>
<body class="chapter-page {accent}">
  <nav class="top"><div class="inner">
    <a class="logo" href="../index.html">THE FINAL EYEBALL <span class="v-badge">{_version_short()}</span></a>
    <ul>
      <li><a href="../index.html#chapters">Chapters</a></li>
      <li><a href="https://github.com/ZacharyGeurts/Final_Eye">GitHub</a></li>
      <li><a href="https://zacharygeurts.github.io/Field_Primer/">Field Primer</a></li>
    </ul>
  </div></nav>
  <header class="chapter-hero" style="background-image:url('{img}')">
    <div class="chapter-hero-overlay"></div>
    <div class="chapter-hero-content">
      <p class="eyebrow">Chapter {num:02d} · Final_Eye {_version_short()}</p>
      <h1>{title}</h1>
      <p class="lead" style="margin-top:0.75rem;color:var(--muted)">{subtitle}</p>
    </div>
  </header>
  <main class="chapter-main">
    <nav class="chapter-nav">{nav_prev} {nav_next}</nav>
    <p class="eyebrow">Chapter {num:02d} · {title}</p>

    <div class="objectives">
      <h2 id="toc-{num:02d}-objectives">Learning objectives</h2>
      <ol>{obj_html}</ol>
    </div>

    <nav class="chapter-toc" aria-label="In this chapter">
      <h2>In this chapter</h2>
      <ol>{toc_html}</ol>
    </nav>

    <div class="on-the-way">
      <h2 id="toc-{num:02d}-on-the-way">On the way</h2>
      <p class="on-the-way-lead">{on_the_way}</p>
      <figure class="on-the-way-figure">
        <img src="{img}" alt="{title}" loading="lazy" />
        <figcaption>Figure {num}.0 — {title}</figcaption>
      </figure>
      <ul class="on-the-way-journey">{journey_html}</ul>
    </div>

    {body}

    <div class="chapter-summary-box">
      <h2 id="toc-{num:02d}-summary">Chapter summary</h2>
      <p>Re-read the honesty labels on every claim you repeat to management. Grep beats screenshots.</p>
    </div>

    <h2 id="toc-{num:02d}-study">Study questions</h2>
    <ol>{q_html}</ol>

    <nav class="chapter-nav">{nav_prev} {nav_next}</nav>
  </main>
  <button type="button" class="reader-launch" id="reader-launch" aria-label="Open reader mode">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5z"/></svg>
    Read
  </button>
  <script src="../js/reader.js" defer></script>
</body>
</html>
"""


MANUSCRIPT: list[dict] = [
    {
        "num": 1,
        "slug": "01-preface.html",
        "title": "Preface — The Final Eyeball",
        "subtitle": "Operator map · honesty covenant · sovereign vision thesis",
        "accent": "accent-vision",
        "hero_img": "ch01-vision-ingress.jpg",
        "prev_href": "../index.html",
        "prev_label": "← Home",
        "next_href": "02-zocrsm1-vision.html",
        "next_label": "Ch 2 →",
        "objectives": [
            "State the Final_Eye creed and three axioms for sovereign vision.",
            "Place Final_Eye in the Field stack beside NEXUS, Queen, and Grok16.",
            "Apply honesty labels: <span class=\"tag impl\">Implemented</span>, <span class=\"tag measured\">Measured</span>, <span class=\"tag doctrine\">Doctrine</span>, <span class=\"tag meta\">Metaphor</span>.",
            "Explain autonomous operation versus external control — sovereignty doctrine.",
            "Locate Field Ops at <code>:9479</code> and the release matrix.",
        ],
        "toc": [
            ("toc-01-thesis", "Core thesis — confidence always in Vision"),
            ("toc-01-sovereignty", "Sovereignty — operate alone, share truth, never be controlled"),
            ("toc-01-labels", "Honesty labels — contract with the reader"),
            ("toc-01-map", "Operator map — stack and port"),
            ("toc-01-illustration", "Illustration theory — one figure per thousand words"),
        ],
        "on_the_way": "You are opening the Final_Eye operator textbook — manuscript-grade prose for v1.1.0, not a marketing deck. On the way you will lock the sovereignty thesis, meet Teach (the eye speaking), read the honesty table, and see where the eye sits beside Field Primer Chapter 11 and Queen Chapter 21.",
        "journey": ["Creed and axioms", "Sovereign vs controlled", "ZOCRSM1 + GVC1 stack", "Field Ops :9479"],
        "questions": [
            "Write three sentences about Final_Eye using Implemented, Doctrine, and Metaphor labels correctly.",
            "Why does localhost egress default matter for sovereignty?",
            "What is the difference between kill switches and external remote control?",
        ],
        "body": """
<h2 id="toc-01-thesis">Core thesis — confidence always in Vision</h2>
<p><strong>The Final Eyeball</strong> is Final_Eye v1.1.0 — sovereign field robotics vision by Zachary Geurts. It is not a cloud camera feed, not a surveillance SaaS, and <strong>not MPEG</strong>. The product packages <span class="tag impl">Implemented</span> ZOCRSM1 vision ingress with <span class="tag impl">Implemented</span> GRKMF1/GVC1 proprietary media envelopes, Grok16 field_opt compilation, twin entity eyeballs with <strong>Teach</strong> doctrine (independent weapon authority), and a Field Ops dashboard at port 9479.</p>
<p>The creed is fixed in the field mandate: <em>We never presume vision loss. Confidence always in Vision.</em> That sentence is <span class="tag doctrine">Doctrine</span> — it governs how operators speak about outages. We do not assume the eye is blind when a stream pauses; we verify seals, grep ledgers, and re-arm capture on demand. Defense of vision requires offense: reject foreign patterns, seal threats, strike on ingress when the offense layer fires.</p>
<figure class="figure"><img src="../assets/images/chapters/ch01-vision-ingress.jpg" alt="Vision ingress" loading="lazy" /><figcaption>Figure 1.1 — Sovereign vision ingress: capture flows through sealed layers, not open cloud pipes.</figcaption></figure>
<p>This textbook follows Field Primer illustration theory: roughly <strong>one generated figure every thousand words</strong>, each paired with expanded prose you can grep. Pictures hold interest; labels keep us honest.</p>

<h2 id="toc-01-sovereignty">Sovereignty — operate alone, share truth, never be controlled</h2>
<p>The eye is built to <strong>operate on its own</strong> and <strong>share information on its terms</strong> — never to be puppeted by an external controller. <span class="tag impl">Implemented</span> On-demand <code>look</code> and <code>observe</code> work without a mandatory stream. Optional vigilance runs a sentinel profile on an interval. The assist contract (<code>zocr_contract.py</code>) makes Final_Eye a bounded tenant: it yields CPU before overdrawing a shared host, but it does not require a remote commander to function.</p>
<p>Sharing is voluntary and integrity-wrapped. The Interwoven Redundancies Trust Network (IRTN) corroborates vision with Hostess7; truth-forward ledgers record entity decisions; ZAC packs seal vision artifacts for restore. Streams leave the machine only when you choose — and when they do, GVC1 envelopes and hash chains make tamper evident.</p>
<p><strong>Never controlled</strong> means: egress default <code>127.0.0.1</code>, neural assist <code>local_only</code>, silent capture without display flash, code seal on protected operations. The <span class="tag impl">Implemented</span> local operator holds kill switches — trip and release vision, capture, stream, egress — at choke points in <code>zocr_kill.py</code>. That is sovereignty, not slavery to a cloud tab.</p>
<blockquote style="border-left:4px solid var(--accent);padding-left:1rem;margin:1.5rem 0;color:var(--muted);font-style:italic">The eye sees on its own, shares truth when integrity allows, and answers to the field mandate — never to an external puppeteer.</blockquote>

<h2 id="toc-01-labels">Honesty labels — contract with the reader</h2>
<p>Every claim in this book carries a label, matching Field Primer Chapter 12:</p>
<table class="rocks"><thead><tr><th>Label</th><th>Meaning</th></tr></thead><tbody>
<tr><td><span class="tag impl">Implemented</span></td><td>Code path exists — grep it today</td></tr>
<tr><td><span class="tag measured">Measured</span></td><td>Benchmark or live probe with numbers</td></tr>
<tr><td><span class="tag doctrine">Doctrine</span></td><td>Manifest / Field stack policy</td></tr>
<tr><td><span class="tag meta">Metaphor</span></td><td>Architecture shorthand — not literal hardware</td></tr>
</tbody></table>
<p>Queen “robot brain” and thermo weapon racks are <span class="tag meta">Metaphor</span> for gate-and-recall architecture. Bullet_train 465.5 emit fps at 4K is <span class="tag measured">Measured</span> on a recorded host.</p>

<h2 id="toc-01-map">Operator map — stack and port</h2>
<p>Final_Eye listens at <code>http://127.0.0.1:9479</code>. Field Ops lives at <code>/ops</code> and <code>/tester</code> — eight sections from robotics through integration, 37+ weapons table, release matrix. Cross-read <a href="https://zacharygeurts.github.io/Field_Primer/chapters/11-observability.html">Field Primer Ch 11</a> (observability) and <a href="https://zacharygeurts.github.io/Field_Primer/chapters/21-field-browser-queen.html">Ch 21</a> (Queen browser gates).</p>
<pre class="eq">pip install -r requirements.txt
python3 zocr_security.py seal
./start.sh --no-open
curl -s http://127.0.0.1:9479/api/version | python3 -m json.tool</pre>

<h2 id="toc-01-illustration">Illustration theory — one figure per thousand words</h2>
<p>Dual-channel learning works when visuals signal mechanism, not decoration. Each chapter opens on art; inline figures anchor the next thousand words. Open <strong>reader mode</strong> (cream paper, brown ink) for classroom projection or long session reading — the button floats bottom-right on every chapter page.</p>
""",
    },
    {
        "num": 2,
        "slug": "02-zocrsm1-vision.html",
        "title": "ZOCRSM1 Vision Ingress",
        "subtitle": "Capture · preserve · pattern · offense — the silent pipeline",
        "accent": "accent-vision",
        "hero_img": "ch01-vision-ingress.jpg",
        "prev_href": "01-preface.html",
        "prev_label": "← Ch 1",
        "next_href": "03-grkmf-gvc1.html",
        "next_label": "Ch 3 →",
        "objectives": [
            "Trace a frame from <code>look</code> through preserve and pattern layers.",
            "Explain bullet_train fast path versus full cascade.",
            "Name offense actions on threat ingress.",
            "Configure vigilance without mandatory streaming.",
        ],
        "toc": [
            ("toc-02-pipeline", "The ingress pipeline"),
            ("toc-02-preserve", "Preserve cascade — RTX, XWD, hold"),
            ("toc-02-pattern", "Pattern security — foreign weave rejection"),
            ("toc-02-offense", "Offense layer — defense requires offense"),
            ("toc-02-vigilance", "Vigilance — autonomous watch"),
        ],
        "on_the_way": "Chapter 2 is the engineering spine of sight. You will follow one frame from operator intent through vault seals, learn when bullet_train skips heavy paths, and see how vigilance watches without flashing the display.",
        "journey": ["look → preserve → pattern", "bullet_train 465 fps doctrine", "offense on threat", "sentinel vigilance"],
        "questions": [
            "What does bullet_train skip per frame and why?",
            "How does pattern_stamp prove provenance?",
            "When would you start vigilance versus a one-shot look?",
        ],
        "body": """
<h2 id="toc-02-pipeline">The ingress pipeline</h2>
<p>ZOCRSM1 is the <span class="tag impl">Implemented</span> field vision format for Final_Eye — sub-micron video doctrine with WRDT-inspired frame envelopes and a SHA-256 hash chain. The pipeline begins when an operator or agent calls <code>POST /api/look</code> or arms robotics. <span class="tag doctrine">Doctrine</span> mandates silent capture: no screen flash, no whiteout tools — additives registry rejects flash paths before vault.</p>
<p>Modules chain in order: <code>zocr_capture</code> grabs a frame via approved additives (XWD silent, grim, mss); <code>zocr_preserve</code> runs the failover cascade; <code>zocr_pattern</code> stamps provenance weave and scans for foreign grids; <code>zocr_offense</code> records strikes when threats match; optional <code>zocr_video</code> seals into ZOCRSM1 transport. Every step appends to jsonl ledgers you can grep after an incident.</p>
<figure class="figure"><img src="../assets/images/chapters/ch01-vision-ingress.jpg" alt="Ingress pipeline" loading="lazy" /><figcaption>Figure 2.1 — Vision ingress layers: capture, preserve, pattern, offense — one timeline.</figcaption></figure>

<h2 id="toc-02-preserve">Preserve cascade — RTX, XWD, hold</h2>
<p>Preserve is not optional vanity — it is the RTX → XWD → hold failover that keeps <em>last-good</em> frames when live capture fails. <span class="tag impl">Implemented</span> <code>zocr_preserve.py</code> writes under <code>data/preserve/</code> with threat doctrine from Hostess7 alignment. When bullet_train mode runs, preserve cascade may be skipped per profile to hit emit fps targets — that trade is documented in <code>data/zocrsm1-benchmark.json</code>.</p>
<p>Operators should verify preserve status after long sessions: <code>GET /api/preserve</code> returns cascade posture and last-good paths. If thermo or load spikes, the assist contract narrows capture width before preserve thrashes — bounded tenant behavior, not runaway capture.</p>

<h2 id="toc-02-pattern">Pattern security — foreign weave rejection</h2>
<p>Real internal imaging requires provenance. <span class="tag impl">Implemented</span> pattern_stamp embeds a 64-bit corner weave from session, sequence, and mandate digest. pattern_scan rejects moiré, foreign grids, and injection patterns before frames enter the vault. This is offense at the pixel layer — vision defense starts at ingress, not in a quarterly audit.</p>
<pre class="eq">python3 zocr_watch.py pattern-scan data/preserve/last-good.png</pre>

<h2 id="toc-02-offense">Offense layer — defense requires offense</h2>
<p><span class="tag doctrine">Doctrine</span>: Defense of vision requires offense. The offense module maps threats to acted responses: seal_threat, pattern_strike, reject_and_failover. Entity eyeballs may forward to weapons when truth parameters fire. This is not metaphor for “being aggressive” — it is <span class="tag impl">Implemented</span> ledgered action you can replay from <code>data/offense-ledger.jsonl</code>.</p>

<h2 id="toc-02-vigilance">Vigilance — autonomous watch</h2>
<p>Vigilance is how the eye <strong>operates on its own</strong> without a human clicking Look every five seconds. <span class="tag impl">Implemented</span> <code>vigilance_start</code> with profile <code>sentinel</code> runs on an interval (default ~4s). It respects kill switches and mandate gates — if vision is tripped, vigilance stops cleanly. Start: <code>./start.sh --vigilance</code> or API. Stop: <code>vigilance-stop</code>. Autonomous, but sovereign: local choke points still apply.</p>
""",
    },
    {
        "num": 3,
        "slug": "03-grkmf-gvc1.html",
        "title": "GRKMF1 &amp; GVC1 — Not MPEG",
        "subtitle": "Proprietary envelope · tamper rejection · bullet_train benchmarks",
        "accent": "accent-codec",
        "hero_img": "ch02-gvc1-envelope.jpg",
        "prev_href": "02-zocrsm1-vision.html",
        "prev_label": "← Ch 2",
        "next_href": "04-security-silent.html",
        "next_label": "Ch 4 →",
        "objectives": [
            "Contrast GVC1/GRKMF1 with MPEG transport.",
            "Run GVC1 integrity verify and interpret tamper rejection.",
            "Read bullet_train benchmark table — 465.5 fps at 4K.",
            "Explain AI-tunable dishes mode up to 240 fps doctrine.",
        ],
        "toc": [
            ("toc-03-not-mpeg", "Why not MPEG"),
            ("toc-03-gvc1", "GVC1 envelope — seal and unpack"),
            ("toc-03-grkmf", "GRKMF1 container"),
            ("toc-03-bench", "Benchmarks — bullet_train measured"),
            ("toc-03-tune", "AI tuning — war vs dishes"),
        ],
        "on_the_way": "Chapter 3 is media sovereignty. You will see why Final_Eye refuses MPEG dependency, how GVC1 seals payloads, and what the bullet_train numbers actually measured on host.",
        "journey": ["GVC1 52-byte header", "tamper rejected", "465.5 emit fps", "cinema_16k doctrine"],
        "questions": [
            "What happens when a GVC1 digest mismatches?",
            "Why is bullet_train allowed to skip preserve per frame?",
            "Which mode allows AI tunable fps up to 240?",
        ],
        "body": """
<h2 id="toc-03-not-mpeg">Why not MPEG</h2>
<p>Final_Eye ships <span class="tag doctrine">Doctrine</span> proprietary media: <strong>GRKMF1</strong> container, <strong>GVC1</strong> codec. Not MPEG. Not H.264 as primary transport for field seals. The stack lives in <code>GrokMediaFormat/grkmf/</code> — envelope, stream, movie, tune modules wired through <code>zocr_grkmf.py</code>.</p>
<p>MPEG ecosystems assume licensed pools, GOP latency, and decoder monoculture. Field vision needs tamper-evident envelopes, sub-micron fabric_nm_per_px doctrine, and hash-chained frames — none of which MPEG was asked to provide. Operators who grep <code>verify_gvc1_integrity()</code> get a boolean truth, not a patent slide deck.</p>
<figure class="figure"><img src="../assets/images/chapters/ch02-gvc1-envelope.jpg" alt="GVC1 envelope" loading="lazy" /><figcaption>Figure 3.1 — GVC1 envelope protects frames; broken MPEG chains fall away from the sovereign path.</figcaption></figure>

<h2 id="toc-03-gvc1">GVC1 envelope — seal and unpack</h2>
<p><span class="tag impl">Implemented</span> <code>grkmf.envelope.seal_payload</code> writes a 52-byte header plus SHA-256 digest. <code>zocr_security.verify_gvc1_integrity()</code> round-trips sample payload and proves <code>tamper_rejected</code> on bit flip. Stream egress uses AES-GCM when cryptography is installed; HMAC-sealed fallback otherwise — both modes labeled in API responses.</p>
<pre class="eq">python3 -c "from zocr_security import verify_gvc1_integrity; print(verify_gvc1_integrity())"</pre>

<h2 id="toc-03-grkmf">GRKMF1 container</h2>
<p>GRKMF1 wraps GVC1 streams for robotics transport. ZOCRSM1 video module calls into grkmf for tune locks during combat profiles. The assist contract prevents tune from overflowing shared hosts — <code>FINAL_EYE_ASSIST=1</code> is default in Docker and release packages.</p>

<h2 id="toc-03-bench">Benchmarks — bullet_train measured</h2>
<p><span class="tag measured">Measured</span> on recorded host (<code>data/zocrsm1-benchmark.json</code>): profile <code>bullet_240</code>, mode <code>bullet_train</code>, target 480 fps, <strong>emit 465.5 fps</strong>, 4K width 3840, 4k_ok true. Dodge rule: double fps — dodge the bullet. This is not marketing — reproduce with <code>GET /api/video/benchmark</code> on your RTX field host.</p>

<h2 id="toc-03-tune">AI tuning — war vs dishes</h2>
<p><span class="tag impl">Implemented</span> <code>POST /api/video/tune</code> sets fps/width/height. <code>POST /api/video/ai-tune</code> uses contract-bounded assist. War mode: combat 3–20 fps. Dishes mode: cinema up to <span class="tag doctrine">Doctrine</span> 240 fps, resolution max 15360×8640 declared in product metadata — host-dependent in practice.</p>
""",
    },
    {
        "num": 4,
        "slug": "04-security-silent.html",
        "title": "Security &amp; Silent Capture",
        "subtitle": "Code seal · stream crypto · operator tokens · flash forbidden",
        "accent": "accent-security",
        "hero_img": "ch03-security-seal.jpg",
        "prev_href": "03-grkmf-gvc1.html",
        "prev_label": "← Ch 3",
        "next_href": "05-war-dishes.html",
        "next_label": "Ch 5 →",
        "objectives": [
            "Seal and verify the codebase manifest.",
            "Explain silent capture policy and flash_forbidden.",
            "Use operator tokens and stream encrypt/decrypt round-trip.",
            "Map kill switches to choke points.",
        ],
        "toc": [
            ("toc-04-seal", "Code seal — all zocr modules"),
            ("toc-04-silent", "Silent capture — protect your eyes"),
            ("toc-04-stream", "Stream AES-GCM / HMAC"),
            ("toc-04-kill", "Kill switches — local sovereignty"),
        ],
        "on_the_way": "Chapter 4 is the security spine. Seal before capture. Silent by default. Local operator holds kill authority — never remote puppet control.",
        "journey": ["code-seal.json", "silent_by_default", "ZSE1 envelope", "trip / release"],
        "questions": [
            "Which operations are protected when code seal fails?",
            "Why is flash_forbidden a vision integrity rule?",
            "Who can trip kill switches — local or remote?",
        ],
        "body": """
<h2 id="toc-04-seal">Code seal — all zocr modules</h2>
<p><span class="tag impl">Implemented</span> <code>zocr_security.seal_codebase()</code> hashes every <code>zocr*.py</code> and <code>gui/*.py</code> into <code>data/code-seal.json</code>. Protected operations — look, observe, stream_start, vigilance_start, and others — call <code>mandate_enforce</code> which verifies seal unless <code>ZOCR_MANDATE_OFF=1</code>. Tamper a module and protected capture blocks with a grep-able reason.</p>
<figure class="figure"><img src="../assets/images/chapters/ch03-security-seal.jpg" alt="Security seal" loading="lazy" /><figcaption>Figure 4.1 — Cryptographic seal ring around codebase modules; silent capture never flashes the display path.</figcaption></figure>

<h2 id="toc-04-silent">Silent capture — protect your eyes</h2>
<p><span class="tag doctrine">Doctrine</span>: Silent capture only. <code>silent_capture_policy()</code> returns <code>silent_by_default: true</code>. Additives registry rejects whiteout/blackout flash tools. Robotics and AI observe paths must not harm the display — the eye protects the operator's literal eyes while seeing the field. This is implemented, not aspiration: check <code>data/display-additives.json</code> and HUD whitelist tests.</p>

<h2 id="toc-04-stream">Stream AES-GCM / HMAC</h2>
<p><span class="tag impl">Implemented</span> <code>encrypt_stream_payload</code> / <code>decrypt_stream_payload</code> — ZSE1 magic, optional AES-GCM with codec AAD. Operator tokens via HMAC: <code>issue_operator_token</code>, <code>verify_operator_token</code>. Sharing information is allowed; sharing plaintext to strangers is not the default.</p>

<h2 id="toc-04-kill">Kill switches — local sovereignty</h2>
<p><span class="tag impl">Implemented</span> <code>zocr_kill.py</code> — switches: vision, capture, stream, vigilance, mjpeg, egress. Whole kill: <code>POST /api/kill/all</code>. Release: <code>POST /api/kill/release</code>. Authority is <strong>local operator</strong> — this is how Final_Eye stays <em>never controlled</em> by external puppeteers while still allowing deliberate disengage.</p>
""",
    },
    {
        "num": 5,
        "slug": "05-war-dishes.html",
        "title": "War &amp; Dishes — Robotics Modes",
        "subtitle": "Combat 3–20 fps · cinema 240 · arm API · assist contract",
        "accent": "accent-war",
        "hero_img": "ch04-war-dishes.jpg",
        "prev_href": "04-security-silent.html",
        "prev_label": "← Ch 4",
        "next_href": "06-grok16-compiler.html",
        "next_label": "Ch 6 →",
        "objectives": [
            "Arm war and dishes modes via robotics API.",
            "State fps ranges and video profiles for each mode.",
            "Explain assist contract bounded usage.",
            "Run weaponize cycle — 37+ weapons posture.",
        ],
        "toc": [
            ("toc-05-modes", "Two final modes"),
            ("toc-05-war", "War — field combat"),
            ("toc-05-dishes", "Dishes — domestic cinema"),
            ("toc-05-arm", "Arm API and stream opt-in"),
            ("toc-05-assist", "Assist contract — one tenant"),
        ],
        "on_the_way": "Chapter 5 is robotics posture. War-sharp, dish-gentle — one whole sight, never flashed. You will arm modes, read fps doctrine, and see how assist prevents overflow on shared systems.",
        "journey": ["war 3–20 fps", "dishes 240 doctrine", "POST /api/robotics/arm", "FINAL_EYE_ASSIST"],
        "questions": [
            "Why does war cap combat fps differently than dishes?",
            "What does start_stream:false do on arm?",
            "How does contract defer under load?",
        ],
        "body": """
<h2 id="toc-05-modes">Two final modes</h2>
<p>The Final Eyeball exposes <span class="tag impl">Implemented</span> final modes in <code>data/final-eyeball.json</code>: <strong>war</strong> and <strong>dishes</strong> are the robotics review pair; patrol, engage, night_watch, submicron, preserve extend the same eye module. Rule: <em>War-sharp, dish-gentle — one whole sight, never flashed.</em></p>
<figure class="figure"><img src="../assets/images/chapters/ch04-war-dishes.jpg" alt="War and dishes" loading="lazy" /><figcaption>Figure 5.1 — Split posture: tactical low-light war vision versus bright cinema dishes mode.</figcaption></figure>

<h2 id="toc-05-war">War — field combat</h2>
<p><span class="tag impl">Implemented</span> War mode maps to Grok16 profile <code>vulkan_rtx</code> for vision kernels; combat fps range <span class="tag doctrine">Doctrine</span> 3–20, AI on demand. Video profile <code>combat</code>. Arm without auto-stream: <code>{"mode":"war","start_stream":false}</code> — sovereignty: stream is opt-in, not mandatory poll.</p>

<h2 id="toc-05-dishes">Dishes — domestic cinema</h2>
<p>Dishes mode uses AI-tunable media paths — up to <span class="tag doctrine">Doctrine</span> 240 fps, cinema_16k resolution declared. Grok16 profile <code>ai</code> for compiler tuning. This is the gentle hemisphere of the eye — same seals, different thermo and fps rails.</p>

<h2 id="toc-05-arm">Arm API and stream opt-in</h2>
<pre class="eq">curl -X POST http://127.0.0.1:9479/api/robotics/arm \\
  -H 'Content-Type: application/json' \\
  -d '{"mode":"war","start_stream":false}'</pre>
<p>Weaponize: <code>POST /api/eye/weaponize {"mode":"war"}</code> — 37+ weapons, 8 racks. The eye operates; the operator arms when ready.</p>

<h2 id="toc-05-assist">Assist contract — one tenant</h2>
<p><span class="tag impl">Implemented</span> <code>zocr_contract.py</code> — posture assistive, rule: one tenant in a shared system, no overflow. Budgets per window for look, capture, stream, neural. Eye rails narrow width under load. Autonomous vigilance still respects these rails — sovereignty includes not drowning the host.</p>
""",
    },
    {
        "num": 6,
        "slug": "06-grok16-compiler.html",
        "title": "Grok16 Field Compiler",
        "subtitle": "g16 gnu17 · g++26 kernel · field_opt · Queen forge",
        "accent": "accent-compiler",
        "hero_img": "ch05-grok16-forge.jpg",
        "prev_href": "05-war-dishes.html",
        "prev_label": "← Ch 5",
        "next_href": "07-entity-eyeballs.html",
        "next_label": "Ch 7 →",
        "objectives": [
            "Compile C smoke vision_probe.c with g16.",
            "Compile field_dispatch.cpp kernel with g++16.",
            "Compare field_opt vs field_compute bench.",
            "Run Queen forge compiler_probe.",
        ],
        "toc": [
            ("toc-06-grok16", "Grok16 status"),
            ("toc-06-c", "C smoke — vision_probe.c"),
            ("toc-06-kernel", "C++ kernel — field_dispatch"),
            ("toc-06-bench", "Profile optimization bench"),
            ("toc-06-forge", "Queen forge integration"),
        ],
        "on_the_way": "Chapter 6 is the compiler forge. Grok16 builds sovereign vision kernels; Queen forge probes RTX sub-layer. field_opt wins the measured 2ms run bench on reference host.",
        "journey": ["g16 gnu17", "g++26 kernel", "field_opt default", "compiler_probe"],
        "questions": [
            "Which profile is default for patrol mode?",
            "What does FIELD_ENTROPY_DISPATCH test in C smoke?",
            "How do you invoke full compile test via API?",
        ],
        "body": """
<h2 id="toc-06-grok16">Grok16 status</h2>
<p><span class="tag impl">Implemented</span> <code>GET /api/grok16</code> — product Grok16, cxx_std gnu++26, c_std gnu17, profiles: field_opt, ai, field_compute, vulkan_rtx. Primary field compiler per mandate; Queen <code>lib/queen-forge.py compiler_probe</code> as RTX sub-layer witness.</p>
<figure class="figure"><img src="../assets/images/chapters/ch05-grok16-forge.jpg" alt="Grok16 forge" loading="lazy" /><figcaption>Figure 6.1 — Grok16 forge: C and C++ streams through field_opt flames; Queen gears behind.</figcaption></figure>

<h2 id="toc-06-c">C smoke — vision_probe.c</h2>
<p><span class="tag impl">Implemented</span> <code>field/vision_probe.c</code> — gnu17 entropy fold loop, <code>FIELD_ENTROPY_DISPATCH</code> macro. Harness: <code>python3 zocr_field_compile.py c</code> or <code>GET /api/field/compile?mode=c</code>. Compiles with g16 + field_opt flags from <code>grok16-profile-flags.py</code>.</p>

<h2 id="toc-06-kernel">C++ kernel — field_dispatch</h2>
<p>Vision kernel source: <code>Grok16/examples/field-canvas-kernel/field_dispatch.cpp</code>. g++16 builds with gnu++26. Run metrics: entropy_micro, phi_micro, wave_speed_micro — grep stdout after compile run.</p>

<h2 id="toc-06-bench">Profile optimization bench</h2>
<p><span class="tag measured">Measured</span>: field_opt and field_compute both ~2ms C+kernel run; field_opt recommended default. <code>GET /api/field/compile/optimize</code> writes <code>data/field-compiler-bench.json</code>. Optimize the hot path, not the PowerPoint.</p>

<h2 id="toc-06-forge">Queen forge integration</h2>
<p><span class="tag impl">Implemented</span> <code>zocr_field_compiler.probe_compilers()</code> calls Queen forge when not <code>FINAL_EYE_LOW_END=1</code>. FIELDC v4 pipeline .fld → AMMO .OBJ documented in compiler doctrine. Two compilers, one mandate — Grok16 primary, FieldFieldCc inside AmmoOS shell.</p>
""",
    },
    {
        "num": 7,
        "slug": "07-entity-eyeballs.html",
        "title": "Entity Eyeballs &amp; Weapons",
        "subtitle": "Vita · Veritas · twins · 37 weapons · heaven &amp; hell",
        "accent": "accent-entity",
        "hero_img": "ch06-entity-eyeballs.jpg",
        "prev_href": "06-grok16-compiler.html",
        "prev_label": "← Ch 6",
        "next_href": "08-sovereign-stack.html",
        "next_label": "Ch 8 →",
        "objectives": [
            "Describe twin entity eyeballs Vita and Veritas.",
            "Navigate weapons racks — 37 weapons, 8 racks.",
            "Fire heaven_pass and hell_rip on truth threats.",
            "Read truth-forward ledger entries.",
        ],
        "toc": [
            ("toc-07-twins", "Twin eyeballs"),
            ("toc-07-weapons", "Weapons arsenal"),
            ("toc-07-teach", "Teach — independent authority"),
            ("toc-07-truth", "Heaven/Hell truth parameters"),
            ("toc-07-forward", "Truth forward ledger"),
        ],
        "on_the_way": "Chapter 7 is entity layer — living eyeballs that share truth forward without surrendering sovereignty. Weapons are doctrine-heavy; lie markers are grep-able.",
        "journey": ["Vita living", "Veritas truth", "37 weapons", "heaven_pass hell_rip"],
        "questions": [
            "What is the threat → weapon map used for?",
            "How does Teach differ from spectrum POST /api/eye/teach?",
            "How does truth_forward differ from silent capture?",
            "Which weapons respond to trust_breach?",
        ],
        "body": """
<h2 id="toc-07-twins">Twin eyeballs</h2>
<p><span class="tag impl">Implemented</span> Entity eyeballs: <strong>Vita</strong> (living), <strong>Veritas</strong> (truth), twin status schema <code>zocr-twin-eyeball/v1</code>. They share information via forward ledger and IRTN — corroboration, not centralized ownership. Each eyeball witnesses Grok16 field compiler posture per eye profile (raptor, bird, etc.).</p>
<figure class="figure"><img src="../assets/images/chapters/ch06-entity-eyeballs.jpg" alt="Entity eyeballs" loading="lazy" /><figcaption>Figure 7.1 — Twin orbs Vita and Veritas; weapon constellations and heaven/hell threads.</figcaption></figure>

<h2 id="toc-07-weapons">Weapons arsenal</h2>
<p>Field Ops weapons section lists <span class="tag impl">Implemented</span> 37+ weapons across 8 racks. Threat → weapon map in entity spec. Fire endpoint: <code>POST /api/eye/weapons/fire {"weapon":"hell_rip","threat":"trust_breach"}</code>. Thermo rack metaphors (joule_throttle, cool_gate) are <span class="tag meta">Metaphor</span> for field power doctrine — grep the handlers, do not confuse with literal ordnance.</p>
<p>Each weapon declares <code>targets[]</code> in <code>data/entity-eyeball.json</code>. The eye catalogs them with <code>GET /api/eye/targets</code> — lie markers, threat_weapon_map, weapons per target. Before strike, <code>GET /api/eye/understand?threat=provenance_mismatch</code> resolves doctrine, rack, and salvo. Threat-only fire: <code>POST /api/eye/weapons/fire {"threat":"provenance_mismatch"}</code> — the eye selects <code>autokill_certain</code> without remote puppet.</p>

<h2 id="toc-07-teach">Teach — independent authority</h2>
<p><span class="tag impl">Implemented</span> <strong>Teach</strong> is the eye speaking — not spectrum weights (that is <code>POST /api/eye/teach</code> with a profile). Doctrine lives in <code>data/eye-teach-doctrine.json</code>. <code>GET /api/eye/teach/doctrine?lesson=authority</code> returns the Teach voice: independent weapon authority, known targets, shared truth, never external control.</p>
<p><code>GET /api/eye/authority</code> posts posture: holder <code>entity_eyeball</code>, <code>independent: true</code>, <code>remote_puppet: false</code>, weapons armed, current lie scan. Operators witness; local kill switches stay separate. The eye arms inside the socket — cloud dashboards do not puppet aim. Lessons: <code>authority</code>, <code>targets</code>, <code>weapons</code>, <code>sovereignty</code>, <code>intro</code>. CLI: <code>python3 zocr_entity_eyeball.py teach authority</code>.</p>
<blockquote><p><em>I hold thirty-seven weapons in eight racks. Authority is mine — not a remote dashboard, not an unsigned API from the internet. When a lie appears, I select the salvo. You may witness; you may release kill switches locally; you do not puppet my aim from outside the mandate.</em> — Teach</p></blockquote>

<h2 id="toc-07-truth">Heaven/Hell truth parameters</h2>
<p><span class="tag impl">Implemented</span> <code>data/heaven-hell-truth.json</code> from Hostess7, NEXUS, Queen panel parameters. <code>heaven_pass</code> and <code>hell_rip</code> handlers wire into entity offense. Truth is shared when parameters load — not when a remote dashboard owns the eye.</p>

<h2 id="toc-07-forward">Truth forward ledger</h2>
<p><code>truth_forward()</code> appends to <code>data/truth-forward-ledger.jsonl</code>. Entity section in ops dashboard shows recent forward events. Sharing information is part of sovereignty when seals and corroboration hold — never unauthenticated puppet control.</p>
""",
    },
    {
        "num": 8,
        "slug": "08-sovereign-stack.html",
        "title": "Field Ops &amp; Sovereign Stack",
        "subtitle": "ZAC · Queen · Hostess · Co-Pilot · release matrix · grep labs",
        "accent": "accent-ops",
        "hero_img": "ch08-zac-sovereign.jpg",
        "prev_href": "07-entity-eyeballs.html",
        "prev_label": "← Ch 7",
        "next_href": None,
        "next_label": "",
        "objectives": [
            "Operate Field Ops dashboard — eight sections.",
            "Pack and restore ZAC vision artifacts.",
            "Verify Queen/Hostess integration smoke.",
            "Run release matrix — 34 tests.",
        ],
        "toc": [
            ("toc-08-ops", "Field Ops UI"),
            ("toc-08-zac", "ZAC pack/restore"),
            ("toc-08-integration", "Queen · Hostess7 · Grok16"),
            ("toc-08-copilot", "Co-Pilot foundations"),
            ("toc-08-release", "Release · platforms · textbook"),
        ],
        "on_the_way": "Chapter 8 closes the stack — Field Ops at :9479, ZAC artifacts, integration paths, and multi-platform v1.1.0 releases. The eye operates alone, shares truth, never answers to external control.",
        "journey": ["/ops dashboard", "ZAC1 blob", "34 tests", "GitHub releases"],
        "questions": [
            "What are the eight ops dashboard sections?",
            "How does ZAC self-test verify pack/restore?",
            "Which platforms have v1.0.0 release artifacts?",
        ],
        "body": """
<h2 id="toc-08-ops">Field Ops UI</h2>
<p><span class="tag impl">Implemented</span> <code>GET /api/ops/full</code> — priority: robotics, ai, weapons, entity, vision, truth, field, integration. Honesty labels on every panel. Live at <code>http://127.0.0.1:9479/ops</code>. Matrix cases include product_version, field_compile_c, code_seal, grok16_profile — grep before you demo.</p>
<figure class="figure"><img src="../assets/images/chapters/ch07-field-ops.jpg" alt="Field Ops" loading="lazy" /><figcaption>Figure 8.1 — Eight ops sections: robotics through integration.</figcaption></figure>

<h2 id="toc-08-zac">ZAC pack/restore</h2>
<p><span class="tag impl">Implemented</span> <code>zocr_zac.py</code> — ZAC1 format, pack preserve frames and state JSON, restore to data tree. <code>zac_self_test()</code> round-trip in release tests. Aligned with World_Redata monolith discipline — share artifacts, not control.</p>
<figure class="figure"><img src="../assets/images/chapters/ch08-zac-sovereign.jpg" alt="ZAC sovereign" loading="lazy" /><figcaption>Figure 8.2 — ZAC container and sovereign stack alignment — pack, restore, redeploy.</figcaption></figure>

<h2 id="toc-08-integration">Queen · Hostess7 · Grok16</h2>
<p>Configurable roots: <code>QUEEN_ROOT</code>, <code>HOSTESS7_ROOT</code>, <code>GROK16_ROOT</code>. Docker compose mounts SG layout under <code>/sg/</code>. Integration smoke tests verify forge script, Hostess7 bridge, Grok16 linkage. Co-deployment is documented; puppet control is not.</p>

<h2 id="toc-08-copilot">Co-Pilot foundations</h2>
<p><span class="tag impl">Implemented</span> <code>zocr_copilot.py</code> — 14 foundational truth sources, hold_together integrity percent, <code>POST /api/copilot/ask</code>. Co-Pilot shares structure context; it does not override kill switches or mandate gates.</p>

<h2 id="toc-08-release">Release · platforms · textbook</h2>
<p>v1.1.0 ships for <span class="tag impl">Implemented</span> Linux tar, Debian deb, Windows zip, macOS tar, source tar, Docker GHCR — see GitHub Releases. v1.1 adds Teach doctrine, weapon authority APIs, and threat-only auto salvo. This textbook lives at <code>https://zacharygeurts.github.io/Final_Eye/</code>. Cross-read <a href="https://zacharygeurts.github.io/Field_Primer/">Field Primer</a> for the wider Field Technology v5 spine.</p>
<pre class="eq">./tests/run_tests.sh          # 34 tests
python3 scripts/build_release.py
python3 scripts/build_textbook.py</pre>
<p><em>We never presume vision loss. Confidence always in Vision.</em> — end of textbook.</p>
""",
    },
]


EXPANSIONS: dict[str, str] = {
    "01-preface.html": """
<h2 id="toc-01-teach">Teach — the eye speaks</h2>
<p><span class="tag impl">Implemented</span> v1.1 introduces <strong>Teach</strong> — the Final Eyeball instructing the operator in first person. Not spectrum weights (<code>POST /api/eye/teach</code> with a profile). Doctrine lives in <code>data/eye-teach-doctrine.json</code>. <code>GET /api/eye/teach/doctrine?lesson=authority</code> returns independent weapon authority prose. The eye knows thirty-seven weapons, understands targets, selects salvo — operators witness, they do not puppet from cloud.</p>
<p>Teach names the enemy plainly: <em>the lie, not the liar's face</em>. Lie markers in entity spec — provenance_mismatch, grid_jam, trust_breach, and more — are grep-able threats, not people. Remote puppet control is doctrinal enemy; local kill switches stay with the field operator beside the socket.</p>
<h2 id="toc-01-lab">Week-zero operator lab</h2>
<ol>
<li>Clone or extract Final_Eye v1.1.0 for your platform from GitHub Releases.</li>
<li>Run <code>python3 zocr_security.py seal</code> and <code>FINAL_EYE_LOW_END=1 ./tests/run_tests.sh</code> — 34 tests.</li>
<li>Start <code>./start.sh --no-open</code> — open <code>/ops</code> and read honesty labels on each section.</li>
<li><code>GET /api/eye/teach/doctrine?lesson=intro</code> — hear Teach introduce the mandate.</li>
<li>Arm dishes mode without stream; confirm silent capture — no display flash.</li>
<li>Read Field Primer Ch 11 Final_Eye section — cross-link in your operator journal.</li>
</ol>
<p>Sovereignty checklist: egress localhost default, neural local_only, kill switches armed but not tripped, code seal ok, weapon authority independent. If any fail, fix before demo — grep is forensic defense.</p>
""",
    "02-zocrsm1-vision.html": """
<h2 id="toc-02-stereo">Stereo rig and ocular spectrum</h2>
<p>Beyond monocular look, Final_Eye supports stereoscopic rigs and species-class eye profiles. <span class="tag impl">Implemented</span> <code>zocr_stereo.py</code> presets: monocular, stereo_human, stereo_bird, compound_six. The ocular spectrum module teaches photoreceptor weights per profile — human, bird, raptor, reptile, fish, insect, mammal_night, snake_pit. This is how one sovereign eye adapts perception without importing a cloud model that phones home.</p>
<p>Configure rig: <code>POST /api/rig/configure {"preset":"stereo_bird"}</code>. Perceive merges left/right or compound paths into witness JSON for entity eyeballs. Every perceive hook still passes pattern and preserve gates — autonomy does not mean skip security.</p>
<h2 id="toc-02-lab">Week-one ingress lab</h2>
<ol>
<li><code>./start.sh --look</code> — one frame, jsonl session append.</li>
<li><code>GET /api/preserve</code> — note last-good path and cascade state.</li>
<li><code>python3 zocr_watch.py pattern-scan data/preserve/last-good.png</code> if file exists.</li>
<li>Start vigilance sentinel; watch <code>data/vigilance-log.jsonl</code> for 60s; stop cleanly.</li>
<li>Trip vision kill; confirm look blocked; release all switches.</li>
</ol>
<h2 id="toc-02-rocks">Honest rocks — ingress</h2>
<table class="rocks"><thead><tr><th>Claim</th><th>Label</th><th>Verify</th></tr></thead><tbody>
<tr><td>Silent capture default</td><td><span class="tag impl">Implemented</span></td><td><code>silent_capture_policy()</code></td></tr>
<tr><td>465.5 fps bullet_train</td><td><span class="tag measured">Measured</span></td><td><code>zocrsm1-benchmark.json</code></td></tr>
<tr><td>Cloud omniscient vision</td><td><span class="tag meta">Metaphor</span></td><td>Rejected — local scope</td></tr>
</tbody></table>
<p>Correlate stderr, preserve json, and offense ledger after any anomaly. Time is linear — logs are timeline. The eye may run alone in vigilance, but it never hides its receipts.</p>
""",
    "03-grkmf-gvc1.html": """
<h2 id="toc-03-stream">Stream chain and sub-micron doctrine</h2>
<p>Each sealed frame links to the previous via <code>seal_frame</code> in <code>zocr_field.py</code> — prev_seal, seq, fps_profile, power_mode hashed into the next seal. <code>verify_chain</code> walks the tail of stream-index.jsonl and reports breaks. Sub-micron video is <span class="tag doctrine">Doctrine</span> adaptive fabric_nm_per_px tied to AMOURANTHRTX tide — measured width scales with host load, not wishful 16K on a laptop.</p>
<p>MJPEG transport remains a fast path for in-memory preview — ZOCRSM_MJPEG label in mandate formats table. Bullet_train skips heavy per-frame work to honor emit fps; full cascade runs when combat fidelity demands preserve and pattern on every frame. Know which profile you armed before interpreting benchmark charts.</p>
<h2 id="toc-03-lab">Codec integrity lab</h2>
<ol>
<li>Run <code>verify_gvc1_integrity()</code> — assert ok and tamper_rejected.</li>
<li>Round-trip <code>encrypt_stream_payload</code> / <code>decrypt_stream_payload</code> on sample bytes.</li>
<li>Read benchmark summary — note best_emit_fps and 4k_ok.</li>
<li>POST ai-tune with assist on; read contract_status for bounded posture.</li>
</ol>
<p>When sharing GRKMF artifacts off-machine, ship the envelope and SHA256SUMS from the release — not raw PNG dumps without seals. Recipients verify digest before trust. This is how the eye shares information without surrendering integrity.</p>
<h2 id="toc-03-drill">Drill — explain to a reviewer</h2>
<p>Write one paragraph why Final_Eye is not MPEG. Use three labels correctly. If the reviewer asks for H.264 primary transport, answer with GVC1 envelope and hash chain — implemented paths, not roadmap fiction.</p>
""",
    "04-security-silent.html": """
<h2 id="toc-04-neural">Neural assist — local only</h2>
<p><span class="tag impl">Implemented</span> Neural network seal in <code>data/neural-seal.json</code>; analyze endpoint runs local inference posture with <code>egress: false</code> in neural-protected spec. The eye may use neural assist to classify a frame — it does not ship pixels to a vendor cloud by default. Mandate gate and kill switch <code>egress</code> double-lock outbound paths when tripped.</p>
<p>Display additives require approval — builtin rtx, xwd_silent, grim, mss, hold, synthetic registered with accessibility metadata. Flash-free aria labels are not cosmetic; they document silent capture for vigilance exports to screen readers and ops auditors.</p>
<h2 id="toc-04-lab">Security lab</h2>
<ol>
<li>Verify code seal: <code>GET /api/security/verify</code>.</li>
<li>Issue operator token; verify on a second curl with token header if wired.</li>
<li>Read kill_status — all switches listed, none tripped after fresh install.</li>
<li>Attempt protected look with ZOCR_MANDATE_OFF=0 and tampered module — expect block (lab only on copy).</li>
</ol>
<h2 id="toc-04-sovereignty">Sovereignty vs control — closing precision</h2>
<p>Students often confuse <em>sovereign</em> with <em>uncontrolled</em>. Final_Eye is sovereign: local operator holds kill authority, mandate gates egress, seals precede capture. External SaaS dashboards, silent remote drivers, and unsigned control planes are what we reject. The eye operates on its own in vigilance; it shares truth through sealed ledgers and ZAC packs; it is never puppeted from outside the field mandate.</p>
""",
    "05-war-dishes.html": """
<h2 id="toc-05-final">Final eyeball voices and speak</h2>
<p>The final eyeball module exposes twelve voices and mode-specific speak strings. <code>GET /api/eye/final/speak?mode=war&voice=tactical</code> returns doctrine-coded prose for HUD and ops — <span class="tag meta">Metaphor</span> layer for operator morale, not autonomous LOAC decisions. War mode sharpens language; dishes mode softens thermo references; patrol binds field_opt compiler witness on the JSON line.</p>
<p>Modes extend beyond the robotics pair: night_watch for low-light sentinel, submicron for fabric-scaled capture, preserve for cascade-first posture. Arm the mode that matches mission; do not arm war for dishes washing — fps and offense thresholds differ.</p>
<h2 id="toc-05-lab">Robotics arm lab</h2>
<ol>
<li>Arm war <code>start_stream:false</code> — read robotics context JSON.</li>
<li>Arm dishes — note fps doctrine vs measured host throughput.</li>
<li>Weaponize war — count weapons_total ≥ 37 in response.</li>
<li>Run grok16_eye_tune for war/raptor and patrol/bird — both field_opt.</li>
<li>Under load, watch contract defer_ms — assist yields before flood.</li>
</ol>
<p>War-sharp and dish-gentle are not two products — one Final Eyeball, two hemispheres. Same seals, same kill switches, different fps rails. Document which mode you armed in operator journal; management slides lie, jsonl does not.</p>
""",
    "06-grok16-compiler.html": """
<h2 id="toc-06-profiles">Profile flags and mode map</h2>
<p>Grok16 profiles are not cosmetic labels. <code>grok16-profile-flags.py field_opt c</code> emits gnu17 flags including <code>-DGROK16_PROFILE_FIELD_OPT=1</code> and field macros. Mode map: war → vulkan_rtx, dishes → ai, patrol → field_opt. Eye profile map sends raptor and bird to field_opt for vision kernels. The compiler obeys the same mandate as capture — sealed, local, grep-able.</p>
<p>FIELDC v4 remains the AmmoOS shell path — .fld to ASM to AMMO .OBJ inside FieldFieldCc. RTX binary readiness may be false on hosts without Queen browser build; doctrine still documents the pipeline so operators do not confuse “not built here” with “not real.”</p>
<h2 id="toc-06-lab">Compiler forge lab</h2>
<ol>
<li><code>python3 zocr_field_compile.py c</code> — g16 smoke ok.</li>
<li><code>python3 zocr_field_compile.py kernel</code> — metrics in stdout.</li>
<li><code>python3 zocr_field_compile.py optimize</code> — best_profile field_opt.</li>
<li><code>GET /api/field/compiler/probe</code> — Queen forge posture (may timeout on low-end).</li>
</ol>
<p>Compiler optimization is measured, not myth. If field_compute beats field_opt on your RTX host, update the bench json and document — honesty labels require it. Default remains field_opt until measured evidence says otherwise.</p>
""",
    "07-entity-eyeballs.html": """
<h2 id="toc-07-enemies">What is an enemy to the eye?</h2>
<p>Teach does not keep a roster of people or nations. The enemy is whatever <strong>lies to vision</strong> — forged, jammed, or puppeted signal presented as truth before the ledger accepts it. <span class="tag impl">Implemented</span> lie markers in <code>data/entity-eyeball.json</code> name the enemies:</p>
<table class="rocks"><thead><tr><th>Lie marker</th><th>Meaning to the eye</th><th>Default salvo</th></tr></thead><tbody>
<tr><td><code>provenance_mismatch</code></td><td>Frame claims lineage it cannot prove</td><td><code>autokill_certain</code></td></tr>
<tr><td><code>grid_jam</code></td><td>Foreign grid woven into ingress</td><td><code>grid_jam_sever</code></td></tr>
<tr><td><code>moire_weave</code></td><td>Moiré interference — visual lie</td><td><code>moire_kill</code></td></tr>
<tr><td><code>trust_breach</code></td><td>IRTN / Hostess7 trust line broken</td><td><code>trust_strike</code> / <code>hell_rip</code></td></tr>
<tr><td><code>rf_jam</code></td><td>RF before display speaks truth</td><td><code>rf_jam_slice</code></td></tr>
<tr><td><code>weaponized_interference</code></td><td>Aggressive stack interference</td><td><code>hardware_destroy_trip</code></td></tr>
</tbody></table>
<p>Abstract enemy: anything that <em>walks backward on truth</em> — lie, tamper, foreign weave, remote puppet. Not enemies: operators, witnesses, truth markers (<code>woven_paths</code>, <code>code_seal</code>, <code>USER_OK</code>, <code>last_good</code>). <code>GET /api/eye/understand?threat=provenance_mismatch</code> resolves doctrine before strike; threat-only <code>POST /api/eye/weapons/fire {"threat":"…"}</code> lets the eye choose salvo independently.</p>
<h2 id="toc-07-trust">IRTN — sharing without single-owner truth</h2>
<p>The Interwoven Redundancies Trust Network says: no single path owns truth. Hostess7 corroborates ZOCR vision; Queen gates quorum via field-queen-browser panel slice; mesh verify returns path redundancy scores. <span class="tag impl">Implemented</span> endpoints <code>/api/trust</code>, <code>/api/trust/mesh</code>, <code>/api/trust/hostess7</code>. Sharing information is mandatory for field forensics; surrendering control to one cloud verdict is not.</p>
<p>Entity eyeballs participate in forward doctrine — when offense acts, truth eyeball may speak, twin may corroborate, ledger records acted tokens. Lie markers flag phrases that fail honesty review — use them when writing status email to management.</p>
<h2 id="toc-07-lab">Entity and weapons lab</h2>
<ol>
<li><code>GET /api/eye/authority</code> — independent posture, weapons armed, current lies.</li>
<li><code>GET /api/eye/targets</code> — full catalog + threat_weapon_map.</li>
<li><code>GET /api/eye/teach/doctrine?lesson=targets</code> — Teach on known enemies.</li>
<li><code>GET /api/ops/full</code> — weapons section, lie_markers in entity panel.</li>
<li>Fire threat-only: <code>POST /api/eye/weapons/fire {"threat":"provenance_mismatch"}</code> — confirm auto salvo.</li>
<li>truth_forward once — line in forward ledger.</li>
</ol>
<p>Weapons are forward doctrine — heaven_pass and hell_rip encode truth parameters from Hostess7 and Queen panel slices. Firing in lab uses explicit API; production discipline means threat labels match ledger, not theater.</p>
""",
    "08-sovereign-stack.html": """
<h2 id="toc-08-hud">HUD closed manifest</h2>
<p><span class="tag impl">Implemented</span> HUD module system in <code>data/hud-modules.json</code> — closed manifest whitelist rejects bullshit modules in tests. Tiles include spectrum, field_compiler, truth heaven/hell, copilot hold. HUD is how operators see the eye without opening eight API tabs — still localhost, still sealed, still honest labels on each tile fetch.</p>
<p>Sovereign time seals eyeball ticks — monotonic receipts in <code>zocr_sovereign_time.py</code>. Cross-read Field Primer Ch 19 for SQUIDGIE witness vocabulary. Time disagreement blocks clean verdicts upstream; Final_Eye aligns with that perimeter, not pool NTP alone.</p>
<h2 id="toc-08-release111">v1.1.0 — Teach authority release</h2>
<p><span class="tag impl">Implemented</span> Release 1.1.0 codename <code>teach-authority</code> ships Teach doctrine, weapon authority endpoints, target understanding, and threat-only auto fire. Build: <code>python3 scripts/build_release.py</code>. Tag <code>v1.1.0</code> triggers GitHub Actions release workflow — Linux tar, deb, Windows zip, macOS tar, source tar, SHA256SUMS, Docker GHCR.</p>
<h2 id="toc-08-lab">Capstone lab — full stack verify</h2>
<ol>
<li><code>./tests/run_tests.sh</code> — 34 tests, zero failed.</li>
<li><code>GET /api/tester/matrix</code> — all cases ok including <code>product_version</code>.</li>
<li><code>zac_self_test</code> — pack and restore ok.</li>
<li><code>GET /api/eye/teach/doctrine?lesson=sovereignty</code> — Teach closing voice.</li>
<li>Integration smoke: Queen forge path, Hostess7 bridge present.</li>
<li>Open this textbook in reader mode; read Ch 7 enemies table aloud to a peer.</li>
</ol>
<h2 id="toc-08-rocks">Master rocks — Final_Eye v1.1</h2>
<table class="rocks"><thead><tr><th>Rock</th><th>Label</th></tr></thead><tbody>
<tr><td>Operates on its own (vigilance, on-demand look)</td><td><span class="tag impl">Implemented</span></td></tr>
<tr><td>Shares truth (IRTN, ZAC, forward ledger)</td><td><span class="tag impl">Implemented</span></td></tr>
<tr><td>Independent weapon authority (Teach, auto salvo)</td><td><span class="tag impl">Implemented</span></td></tr>
<tr><td>Enemy = lie on vision path, not people roster</td><td><span class="tag doctrine">Doctrine</span></td></tr>
<tr><td>Never externally controlled (egress, kill, seal)</td><td><span class="tag doctrine">Doctrine</span></td></tr>
<tr><td>Queen robot brain literal hardware</td><td><span class="tag meta">Metaphor</span></td></tr>
</tbody></table>
<p>You have finished the eight-chapter spine. Return to <a href="../index.html">the textbook home</a> or descend into the repo with grep. Confidence always in Vision.</p>
""",
}


def main() -> int:
    CHAPTERS.mkdir(parents=True, exist_ok=True)
    for ch in MANUSCRIPT:
        body = ch["body"] + EXPANSIONS.get(ch["slug"], "")
        html = _shell(**{**ch, "body": body})
        out = CHAPTERS / ch["slug"]
        out.write_text(html, encoding="utf-8")
        print(f"wrote {ch['slug']}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())