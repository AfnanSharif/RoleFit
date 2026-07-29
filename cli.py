from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
from resume_analyzer.providers import openai_embedding_similarity


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare a resume with a target role")
    parser.add_argument("resume", type=Path)
    parser.add_argument("job_description", type=Path)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--openai-embeddings", action="store_true", help="Use contact-redacted hosted embeddings")
    args = parser.parse_args()
    resume_text, job_text = extract_text(args.resume), extract_text(args.job_description)
    analysis = ResumeAnalyzer().analyze(resume_text, job_text)
    if args.openai_embeddings:
        semantic = round(openai_embedding_similarity(resume_text, job_text) * 100, 1)
        analysis.scores.content_similarity = semantic
        analysis.scores.overall = round(0.45 * analysis.scores.skill_coverage + 0.35 * semantic + 0.20 * analysis.scores.resume_quality, 1)
        analysis.provider = "Offline evidence + contact-redacted OpenAI embeddings"
    content = json.dumps(analysis.to_dict(), indent=2) if args.format == "json" else analysis.to_markdown()
    if args.output:
        args.output.write_text(content, encoding="utf-8")
        print(f"Created {args.output.resolve()}")
    else:
        print(content)


if __name__ == "__main__":
    main()
