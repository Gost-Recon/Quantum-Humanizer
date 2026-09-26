# AI Humanizer Suite — Render deploy (free, no card)

Render's free tier is the one free host that also accepts a **custom domain**
(if you ever buy one — the only cost in this whole project).

## Steps
1. Sign up at render.com (email or GitHub — no card asked).
2. New → Blueprint. Point it at the GitHub repo containing this folder
   (`render.yaml` does the configuration: free plan, Streamlit start command).
3. Deploy. First boot has a ~50 s cold start; afterwards it sleeps when idle.
4. URL: `https://ai-humanizer-suite.onrender.com` (prefix yours to choose).

## Optional custom domain (costs only the domain itself)
Render → Settings → Custom Domains → add your domain, set the DNS records
it shows at your registrar.

## Notes
- Free services sleep after 15 min idle; first visitor waits ~50 s.
- Set `GROQ_API_KEY` under Environment for the optional LLM polish layer.
- If the key is absent the deterministic engine runs — never a silent failure.
