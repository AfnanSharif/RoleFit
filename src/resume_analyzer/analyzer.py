from __future__ import annotations

import re
from collections import Counter

from .models import ResumeAnalysis, ScoreBreakdown
from .text import cosine_similarity, keyword_gaps, normalize, tokens

SKILLS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "sql", "nosql",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "linux", "git", "spark", "hadoop",
    "pandas", "numpy", "pytorch", "tensorflow", "scikit-learn", "machine learning", "deep learning",
    "nlp", "llm", "rag", "langchain", "fastapi", "flask", "django", "react", "node.js",
    "tableau", "power bi", "excel", "statistics", "a/b testing", "airflow", "dbt", "snowflake",
    "communication", "leadership", "stakeholder management", "project management", "agile", "scrum",
    "rest api", "microservices", "ci/cd", "data modeling", "data visualization", "product management",
}
ACTION_VERBS = {"accelerated", "achieved", "automated", "built", "created", "delivered", "designed", "developed", "drove", "improved", "increased", "launched", "led", "optimized", "reduced", "scaled", "streamlined"}


def _contains(text: str, phrase: str) -> bool:
    return bool(re.search(rf"(?<![\w+]){re.escape(phrase)}(?![\w+])", text.lower()))


def extract_skills(text: str) -> set[str]:
    return {skill for skill in SKILLS if _contains(text, skill)}


def _ats_checks(resume: str) -> tuple[list[dict], float]:
    lowered = resume.lower()
    sections = {name: name in lowered for name in ("experience", "education", "skills")}
    bullets = [line for line in resume.splitlines() if line.strip().startswith(("-", "•", "*"))]
    quantified = sum(bool(re.search(r"\b\d+(?:\.\d+)?%?|\$\d+", line)) for line in bullets)
    action_led = sum(next(iter(tokens(line)), "") in ACTION_VERBS for line in bullets)
    length = len(resume.split())
    checks = [
        {"name": "Core sections", "passed": all(sections.values()), "detail": "Experience, education, and skills headings found" if all(sections.values()) else "Add clear Experience, Education, and Skills headings"},
        {"name": "Evidence-rich bullets", "passed": quantified >= max(1, len(bullets) // 4), "detail": f"{quantified} of {len(bullets)} bullets include a number" if bullets else "No standard bullet points found"},
        {"name": "Action-led writing", "passed": action_led >= max(1, len(bullets) // 3), "detail": f"{action_led} bullets begin with a strong action verb"},
        {"name": "Scannable length", "passed": 180 <= length <= 1200, "detail": f"Approximately {length} words"},
        {"name": "Contact channel", "passed": bool(re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", resume)), "detail": "Email found" if "@" in resume else "Add a professional email address"},
    ]
    return checks, 100 * sum(item["passed"] for item in checks) / len(checks)


class ResumeAnalyzer:
    def analyze(self, resume: str, job_description: str) -> ResumeAnalysis:
        resume, job_description = normalize(resume), normalize(job_description)
        if len(resume) < 120:
            raise ValueError("Resume text is too short for a meaningful analysis")
        if len(job_description) < 100:
            raise ValueError("Job description is too short for a meaningful analysis")
        resume_skills = extract_skills(resume)
        job_skills = extract_skills(job_description)
        matched = sorted(resume_skills & job_skills)
        missing = sorted(job_skills - resume_skills)
        skill_score = 100 * len(matched) / len(job_skills) if job_skills else 50.0
        similarity = 100 * cosine_similarity(resume, job_description)
        checks, quality = _ats_checks(resume)
        overall = 0.45 * skill_score + 0.35 * similarity + 0.20 * quality
        strengths = []
        if matched:
            strengths.append(f"Direct evidence for {len(matched)} requested skill(s): {', '.join(matched[:8])}.")
        if quality >= 60:
            strengths.append("The document passes most basic ATS-readiness checks.")
        if re.search(r"\b\d+(?:\.\d+)?%|\$\d+", resume):
            strengths.append("Includes quantified outcomes that make impact easier to assess.")
        if not strengths:
            strengths.append("The resume provides usable experience text to tailor more directly to this role.")
        improvements = []
        if missing:
            improvements.append(f"If accurate, show evidence for priority gaps such as {', '.join(missing[:6])}; do not add unsupported skills.")
        failed = [item["detail"] for item in checks if not item["passed"]]
        improvements.extend(failed[:3])
        if similarity < 35:
            improvements.append("Mirror the role's language in relevant bullets and connect achievements to its core responsibilities.")
        evidence = [{"skill": skill, "resume_mentions": len(re.findall(re.escape(skill), resume.lower())), "job_mentions": len(re.findall(re.escape(skill), job_description.lower()))} for skill in matched]
        return ResumeAnalysis(
            ScoreBreakdown(round(overall, 1), round(skill_score, 1), round(similarity, 1), round(quality, 1)),
            matched,
            missing,
            strengths,
            improvements,
            keyword_gaps(resume, job_description),
            checks,
            evidence,
            metadata={"resume_words": len(resume.split()), "job_words": len(job_description.split()), "job_skills_detected": len(job_skills)},
        )
