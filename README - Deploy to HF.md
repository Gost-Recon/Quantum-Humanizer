# Deploying AI Humanizer Suite on Hugging Face Spaces — step by step

Goal: a free public URL, no credit card, no GitHub needed.

## Step 1 — Create the Space
1. Sign in on huggingface.co, go to https://huggingface.co/new-space
2. Space name: `ai-humanizer-suite`
3. **Select the Space SDK: Streamlit**
4. Visibility: **Public** (free tier requires public Spaces)
5. Click **Create Space**.

## Step 2 — Upload the files
1. Files and versions tab → Add file → Upload files
2. Upload: `app.py`, `engine.py`, `requirements.txt`
3. Add the theme manually if the uploader skips hidden folders:
   Add file → Create a new file, name it exactly `.streamlit/config.toml`,
   paste the contents of this folder's `.streamlit/config.toml`, commit.
4. Commit. Build takes 2–5 minutes.

## Step 3 — Verify
- When the logs show "Running", open `https://YOUR-USERNAME-ai-humanizer-suite.hf.space`
- Paste the test paragraph from the main README and check the Before/After scores.

## Step 4 — Updates
Edit app.py or engine.py on the Space directly, or re-upload. It rebuilds automatically.

## Optional LLM polish
Space Settings → Secrets → add `GROQ_API_KEY`. Free Groq keys need no credit card.
If the key is missing or expired, the app runs the deterministic engine — clearly
labeled, never a silent failure.

## Free-tier notes
- Sleeps after ~48 h of inactivity; visiting the URL wakes it.
- Keep the Space public; private Spaces need a paid plan for visitors.

## Troubleshooting
| Problem | Fix |
|---|---|
| Build error on streamlit version | Keep `streamlit>=1.30` in requirements.txt |
| Blank app / import error | Check Logs; usually a missing dependency |
| Theme missing | Re-add `.streamlit/config.toml` manually |
