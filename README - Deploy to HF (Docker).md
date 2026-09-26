# AI Humanizer Suite — HF Spaces (Docker) deploy

1. Create a new Space at huggingface.co/new-space, SDK: **Docker**, Visibility: Public.
2. Upload `Dockerfile`, `app.py`, `engine.py`, `requirements.txt`, and `.streamlit/config.toml`.
3. The Space builds and serves on port 7860 (the only port HF allows).
4. URL: `https://YOUR-USERNAME-<space-name>.hf.space`

Optional LLM polish: add `GROQ_API_KEY` under Space Settings → Secrets. Without it the
deterministic engine runs — no silent failure.
