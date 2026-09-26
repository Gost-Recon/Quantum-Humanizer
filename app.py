
"""AI Humanizer Suite - Streamlit app. Deterministic core; optional Groq polish."""
import streamlit as st, json, random
import engine

st.set_page_config(page_title="AI Humanizer Suite", page_icon=":pencil2:", layout="wide")

st.title("AI Humanizer Suite")
st.caption("Deterministic text humanization. Heuristic scores are heuristics - not detector verdicts.")

with st.sidebar:
    st.header("Settings")
    strength = st.slider("Humanization strength", 0.0, 1.0, 0.8, 0.05,
                         help="Higher = more aggressive restructuring.")
    seed = st.number_input("Seed (reproducible output)", 0, 999999, 42)
    st.markdown("---")
    st.caption("Optional LLM polish: set GROQ_API_KEY as a secret to enable. "
               "If unavailable, the app degrades to the deterministic engine - never fails silently.")

default_text = ""
uploaded = st.file_uploader("Upload a .txt or .md file", type=["txt", "md"])
if uploaded: default_text = uploaded.read().decode("utf-8", "replace")

text = st.text_area("Input text", default_text, height=250,
                    placeholder="Paste AI-generated text here...")

col1, col2, col3 = st.columns([1,1,2])
run = col1.button("Humanize", type="primary", use_container_width=True)
rescore = col2.button("Re-score only", use_container_width=True)

if rescore and text.strip():
    st.subheader("Before - heuristic score")
    st.json(engine.analyze(text))

if run and text.strip():
    result = engine.humanize(text, seed=int(seed), strength=strength)
    out = result["text"]
    st.subheader("Humanized text")
    st.write(out)
    st.download_button("Download as .md", out, "Humanized.md", "text/markdown")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Before**")
        st.json(engine.analyze(text))
    with c2:
        st.markdown("**After**")
        st.json(result["metrics"])
    diff_pct = round(100 * (1 - len(out)/max(1,len(text))), 1)
    st.caption(f"Length change: {diff_pct:+}% | Seed {int(seed)} reproduces this exact output.")

st.markdown("---")
st.caption("Strictly a text-processing tool. Heuristic scores do not represent any commercial AI-detector output. "
           "Use responsibly and in line with your institution's policies.")
