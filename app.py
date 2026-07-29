from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent
try:
    from dotenv import load_dotenv
except ImportError:
    pass
else:
    load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "src"))

from resume_analyzer.analyzer import ResumeAnalyzer
from resume_analyzer.extraction import extract_text
from resume_analyzer.presentation import escape_html
from resume_analyzer.providers import openai_embedding_similarity, openai_feedback

st.set_page_config(page_title="RoleFit Studio", page_icon="◈", layout="wide")
st.markdown("""
<style>
.stApp{background:radial-gradient(circle at 5% 0,#0f766e35,transparent 30%),#071312;color:#e7fffb}.hero{border:1px solid #2dd4bf55;background:linear-gradient(120deg,#0b2c2b,#10253b);padding:2.1rem;border-radius:28px;margin-bottom:1rem;animation:rolefit-enter .55s ease-out both,rolefit-glow 8s ease-in-out infinite}.hero h1{font-size:3.3rem;margin:.15rem 0;color:#ccfbf1}.kicker{color:#5eead4;letter-spacing:.15em;font-size:.8rem}[data-testid="stMetric"]{background:#0d2423;border:1px solid #28504e;padding:1rem;border-radius:16px}.skill{display:inline-block;background:#134e4a;color:#ccfbf1;padding:.3rem .65rem;border-radius:99px;margin:.2rem}
@keyframes rolefit-enter{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes rolefit-glow{50%{border-color:#5eead477;box-shadow:0 18px 52px #0f766e2e}}
@media (prefers-reduced-motion: reduce){.hero{animation:none!important}}
</style><div class="hero"><div class="kicker">CANDIDATE-FIRST · EVIDENCE-LED · PRIVATE BY DEFAULT</div><h1>RoleFit Studio</h1><p>See how your resume maps to a role, find honest gaps, and leave with a concrete tailoring plan.</p></div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Analysis settings")
    use_sample = st.toggle("Load included example", value=True)
    ai_similarity = st.toggle("Use contact-redacted OpenAI embeddings", disabled=not bool(os.getenv("OPENAI_API_KEY")))
    ai_feedback = st.toggle("Add contact-redacted AI feedback", disabled=not bool(os.getenv("OPENAI_API_KEY")))
    st.info("This tool supports a job seeker. It does not infer protected traits or recommend hiring decisions.")

resume_tab, job_tab = st.tabs(["1 · Resume", "2 · Job description"])
with resume_tab:
    uploaded = st.file_uploader("Upload resume", type=["txt", "md", "pdf", "png", "jpg", "jpeg", "webp", "tiff"])
    default_resume = (ROOT / "sample_data" / "resume.txt").read_text(encoding="utf-8") if use_sample else ""
    resume_text = st.text_area("Or paste resume text", default_resume, height=330)
with job_tab:
    default_job = (ROOT / "sample_data" / "job-description.txt").read_text(encoding="utf-8") if use_sample else ""
    job_text = st.text_area("Paste the target job description", default_job, height=390)

if st.button("Analyze alignment", type="primary", use_container_width=True):
    try:
        if uploaded:
            with tempfile.TemporaryDirectory() as folder:
                resume_path = Path(folder) / ("resume" + Path(uploaded.name).suffix.lower())
                resume_path.write_bytes(uploaded.getvalue())
                resume_text = extract_text(resume_path)
        analysis = ResumeAnalyzer().analyze(resume_text, job_text)
        if ai_similarity:
            semantic = round(openai_embedding_similarity(resume_text, job_text) * 100, 1)
            analysis.scores.content_similarity = semantic
            analysis.scores.overall = round(0.45 * analysis.scores.skill_coverage + 0.35 * semantic + 0.20 * analysis.scores.resume_quality, 1)
            analysis.provider = "Offline evidence + contact-redacted OpenAI embeddings"
        if ai_feedback:
            analysis.improvements.extend(openai_feedback(resume_text, job_text))
            analysis.provider += " + OpenAI feedback"
        st.session_state["analysis"] = analysis
    except Exception as exc:
        st.error(str(exc))

if analysis := st.session_state.get("analysis"):
    scores = analysis.scores
    cols = st.columns(4)
    cols[0].metric("Overall alignment", f"{scores.overall:.0f}/100")
    cols[1].metric("Skills covered", f"{scores.skill_coverage:.0f}%")
    cols[2].metric("Content similarity", f"{scores.content_similarity:.0f}%")
    cols[3].metric("Resume quality", f"{scores.resume_quality:.0f}%")
    st.progress(scores.overall / 100)
    strengths, gaps, ats, evidence = st.tabs(["Strengths & plan", "Skill map", "ATS readiness", "Evidence"])
    with strengths:
        left, right = st.columns(2)
        with left:
            st.subheader("What already works")
            for item in analysis.strengths:
                st.success(item)
        with right:
            st.subheader("Highest-value improvements")
            for index, item in enumerate(analysis.improvements, 1):
                st.markdown(f"**{index}.** {item}")
    with gaps:
        st.subheader("Matched")
        st.markdown("".join(f"<span class='skill'>✓ {escape_html(skill)}</span>" for skill in analysis.matched_skills) or "No catalogued skills matched.", unsafe_allow_html=True)
        st.subheader("Potential gaps — add only when true")
        for skill in analysis.missing_skills or ["No prominent catalogued gaps"]:
            st.warning(skill)
        st.caption("Other job keywords: " + " · ".join(analysis.keyword_gaps))
    with ats:
        for check in analysis.ats_checks:
            (st.success if check["passed"] else st.warning)(f"**{check['name']}** — {check['detail']}")
    with evidence:
        st.dataframe(analysis.evidence, use_container_width=True, hide_index=True)
        st.caption(f"Method: TF-IDF cosine, explicit skill phrase matching, and five document checks. Provider: {analysis.provider}.")
    st.warning(analysis.disclaimer)
    d1, d2 = st.columns(2)
    d1.download_button("Download report", analysis.to_markdown(), "resume-alignment.md", "text/markdown", use_container_width=True)
    d2.download_button("Download JSON", json.dumps(analysis.to_dict(), indent=2), "resume-alignment.json", "application/json", use_container_width=True)
