from dataclasses import asdict, dataclass, field


@dataclass
class ScoreBreakdown:
    overall: float
    skill_coverage: float
    content_similarity: float
    resume_quality: float


@dataclass
class ResumeAnalysis:
    scores: ScoreBreakdown
    matched_skills: list[str]
    missing_skills: list[str]
    strengths: list[str]
    improvements: list[str]
    keyword_gaps: list[str]
    ats_checks: list[dict]
    evidence: list[dict]
    disclaimer: str = "Career guidance only—not a hiring decision. Verify suggestions and never add experience you do not have."
    provider: str = "Transparent offline analyzer"
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_markdown(self) -> str:
        matched = ", ".join(self.matched_skills) or "None found"
        missing = ", ".join(self.missing_skills) or "No prominent gaps detected"
        strengths = "\n".join(f"- {item}" for item in self.strengths)
        improvements = "\n".join(f"- {item}" for item in self.improvements)
        checks = "\n".join(f"- {'✅' if item['passed'] else '⚠️'} {item['name']}: {item['detail']}" for item in self.ats_checks)
        return f"""# Resume alignment report

**Overall alignment: {self.scores.overall:.0f}/100**

| Dimension | Score |
|---|---:|
| Skills | {self.scores.skill_coverage:.0f}% |
| Content similarity | {self.scores.content_similarity:.0f}% |
| Resume quality | {self.scores.resume_quality:.0f}% |

## Matched skills

{matched}

## Potential skill gaps

{missing}

## Strengths

{strengths}

## Improvements

{improvements}

## ATS-readiness checks

{checks}

> {self.disclaimer}
"""
