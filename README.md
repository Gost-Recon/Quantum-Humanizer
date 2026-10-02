AI Humanizer Suite
Deterministic text humanization, built in the same doctrine as the PSX Terminal
Intelligence Suite: no invented data, no fake scores, no silent failures.

What it does
Transforms AI-generated prose into natural human rhythm:

Strips stock AI phrases (“delve”, “moreover”, “in today’s fast-paced world”, …)
Applies contractions and plain-word swaps (“utilize” → “use”)
Restructures long sentences; merges short ones (burstiness injection)
Varies sentence rhythm; removes em-dash sprawl
The score, stated honestly
The Before/After “AI-likeness” number is a heuristic computed from sentence
length variance, marker density and contraction usage. It is NOT a commercial
detector verdict (GPTZero, Originality.ai, etc. are paid, card-gated services
and are deliberately not used). Treat the score as a directional indicator only.

Files
app.py — Streamlit interface
engine.py — deterministic humanization engine (pure Python, no dependencies)
.streamlit/config.toml — dark theme
HF Spaces Deploy/ — easiest path (upload 3 files, done)
HF Docker Deploy/ — Docker SDK variant, port 7860
Render Deploy/ — Blueprint deploy; the only free host that also accepts a custom domain
Optional LLM polish (free, no card)
Set GROQ_API_KEY (free key from console.groq.com) as a secret on any host.
Note: the current build ships the deterministic engine only; the Groq polish
pass is a planned layer and the sidebar reflects that honestly.

Reproducibility
Seed is user-controlled: same seed + same text + same strength = byte-identical
output. Useful for A/B comparison.

Zero-investment summary
Cost item	Amount
Hosting (Streamlit Cloud / HF Spaces / Render)	0
Domain	0 (free subdomain; custom domain later if ever justified)
API	0 (deterministic core; Groq free tier optional)
Credit card required	None
Test paragraph
In today’s fast-paced world, educational leadership plays a pivotal role in
fostering institutional development. Moreover, it is important to note that
effective leaders utilize robust strategies in order to facilitate
organizational change. Furthermore, instructional supervision has become a
crucial multifaceted landscape that underscores the significance of continuous
professional growth in the ever-evolving realm of education.

Expected: Before score ~60–75, After score ~15–25, contractions and plain words
throughout, no stock phrases remaining.

Changelog
v1.1 (2026-10-01): burstiness overhaul — enforced sentence-length spread (stdev ~5-12 vs ~2 before), single-pass synonym flip (no chained replacements like “in the end -> in the finish”), 21 protected multiword compounds (machine learning, AI, etc. no longer mangled), rotating connector deck (no “even so, even so,” repetition), grammar fixes (“assist X grow” class eliminated), 20-seed regression battery clean.
