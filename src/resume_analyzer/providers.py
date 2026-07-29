from __future__ import annotations

import json
import math
import os

from .text import redact_personal_data


def openai_embedding_similarity(resume: str, job: str) -> float:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install openai for hosted embeddings") from exc
    result = OpenAI().embeddings.create(model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"), input=[redact_personal_data(resume), job])
    left, right = result.data[0].embedding, result.data[1].embedding
    dot = sum(a * b for a, b in zip(left, right))
    norm = math.sqrt(sum(a * a for a in left) * sum(b * b for b in right))
    return dot / norm if norm else 0.0


def openai_feedback(resume: str, job: str) -> list[str]:
    """Return optional contact-redacted feedback; never asks for a hiring decision."""
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install openai for AI feedback") from exc
    prompt = f"""Give 4 factual resume-improvement suggestions as a JSON object with a `suggestions` array.
Use only supplied evidence. Do not infer protected traits, rate the candidate, make a hiring decision, or invent achievements.
JOB:\n{job}\n\nREDACTED RESUME:\n{redact_personal_data(resume)}"""
    response = OpenAI().chat.completions.create(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"}, temperature=0.1)
    data = json.loads(response.choices[0].message.content)
    return [str(item) for item in data.get("suggestions", [])][:4]
