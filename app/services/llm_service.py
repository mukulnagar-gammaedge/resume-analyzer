from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from groq import Groq

from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)


def _clean_llm_text(text: str) -> str:
    """Remove markdown fences and trim."""
    text = (text or "").strip()
    text = re.sub(r"```json|```", "", text).strip()
    return text


def _extract_first_json_object(text: str) -> Dict[str, Any]:
    """
    Extract the first top-level JSON object from a string.
    Handles cases where the model adds commentary before/after JSON.
    """
    text = _clean_llm_text(text)

    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        raise json.JSONDecodeError("No JSON object found", text, 0)

    candidate = text[first:last + 1]
    return json.loads(candidate)


def _chat_json(prompt: str, temperature: float = 0.0) -> Dict[str, Any]:
    """
    Calls Groq Chat Completions and returns a parsed JSON object robustly.
    Uses settings.GROQ_MODEL.
    """
    if not getattr(settings, "GROQ_MODEL", None):
        raise RuntimeError("GROQ_MODEL is not set. Add GROQ_MODEL in your .env")

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )

    content = (response.choices[0].message.content or "").strip()

    try:
        return _extract_first_json_object(content)
    except json.JSONDecodeError:
        # Debug: show raw content to understand model drift
        print("Invalid JSON from LLM (raw):\n", content)
        raise


# -------------------------------------------------
# Resume Structured Extraction
# -------------------------------------------------
def extract_resume_structured(text: str) -> dict:
    prompt = f"""
You are a JSON generator.

Return ONLY valid JSON.
No explanations.
No markdown.
If a field is not found, return a sensible empty value.

Schema:
{{
  "skills": [],
  "total_experience_years": 0,
  "education": "",
  "projects": []
}}

Rules:
- skills must be short skill tokens (1-3 words). Example: "Python", "FastAPI", "PostgreSQL", "Docker".
- projects must be short titles (not paragraphs).

Resume:
{text}
"""

    try:
        data = _chat_json(prompt, temperature=0.0)
    except Exception:
        # Safe fallback
        return {
            "skills": [],
            "total_experience_years": 0,
            "education": "",
            "projects": [],
        }

    # Normalize outputs defensively
    skills = data.get("skills") if isinstance(data.get("skills"), list) else []
    projects = data.get("projects") if isinstance(data.get("projects"), list) else []
    education = data.get("education") if isinstance(data.get("education"), str) else ""
    exp = data.get("total_experience_years", 0)

    # Try coerce exp to number
    try:
        exp = float(exp)
    except Exception:
        exp = 0

    # Normalize skill tokens (strip, dedupe)
    norm_skills = []
    seen = set()
    for s in skills:
        if not isinstance(s, str):
            continue
        token = s.strip()
        if not token:
            continue
        key = token.lower()
        if key not in seen:
            seen.add(key)
            norm_skills.append(token)

    return {
        "skills": norm_skills,
        "total_experience_years": exp,
        "education": education.strip(),
        "projects": [p.strip() for p in projects if isinstance(p, str) and p.strip()],
    }


# -------------------------------------------------
# JD Structured Extraction
# -------------------------------------------------
def extract_jd_structured(text: str) -> dict:
    prompt = f"""
You are a JSON generator.

Return ONLY valid JSON.
No explanations.
No markdown.
If a field is not found, return a sensible empty value.

Schema:
{{
  "required_skills": [],
  "optional_skills": [],
  "min_experience_years": 0
}}

Rules:
- required_skills and optional_skills MUST be short skill tokens only (1-3 words).
  Good: "Python", "PostgreSQL", "Docker", "Kubernetes", "Redis", "CI/CD"
  Bad: "Proficiency in at least one backend language such as Python..."
- Do not include sentences in skills.
- min_experience_years must be a number (0 if not specified).

Job Description:
{text}
"""

    try:
        data = _chat_json(prompt, temperature=0.0)
    except Exception:
        return {
            "required_skills": [],
            "optional_skills": [],
            "min_experience_years": 0,
        }

    req = data.get("required_skills") if isinstance(data.get("required_skills"), list) else []
    opt = data.get("optional_skills") if isinstance(data.get("optional_skills"), list) else []
    min_exp = data.get("min_experience_years", 0)

    # Coerce min_exp
    try:
        min_exp = float(min_exp)
    except Exception:
        min_exp = 0

    def normalize_skill_list(items):
        out = []
        seen = set()
        for s in items:
            if not isinstance(s, str):
                continue
            token = s.strip()
            if not token:
                continue
            # Hard guard: if it's a sentence, drop it
            if len(token.split()) > 6:
                continue
            key = token.lower()
            if key not in seen:
                seen.add(key)
                out.append(token)
        return out

    return {
        "required_skills": normalize_skill_list(req),
        "optional_skills": normalize_skill_list(opt),
        "min_experience_years": min_exp,
    }


# -------------------------------------------------
# Qualitative Analysis
# -------------------------------------------------
def generate_qualitative_analysis(resume_text: str, jd_text: Optional[str]):
    prompt = f"""
You are a JSON generator.

Return ONLY valid JSON.
No explanations.
No markdown.

Schema:
{{
  "strengths": [],
  "weaknesses": [],
  "summary": ""
}}

Rules:
- strengths/weaknesses: short bullet-like strings (max 12 words each)
- summary: 1-3 sentences, professional tone

Resume:
{resume_text}

Job Description:
{jd_text if jd_text else "Not provided"}
"""

    try:
        data = _chat_json(prompt, temperature=0.3)
    except Exception:
        return {
            "strengths": [],
            "weaknesses": [],
            "summary": "",
        }

    strengths = data.get("strengths") if isinstance(data.get("strengths"), list) else []
    weaknesses = data.get("weaknesses") if isinstance(data.get("weaknesses"), list) else []
    summary = data.get("summary") if isinstance(data.get("summary"), str) else ""

    def normalize_list(items):
        out = []
        for s in items:
            if isinstance(s, str) and s.strip():
                out.append(s.strip())
        return out

    return {
        "strengths": normalize_list(strengths),
        "weaknesses": normalize_list(weaknesses),
        "summary": summary.strip(),
    }
