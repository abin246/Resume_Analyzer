import re
from collections import Counter

from app.schemas import ResumeAnalysis, ScoreBreakdown


STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "are", "our", "from", "that", "this", "will",
    "have", "has", "into", "using", "use", "their", "they", "them", "about", "role", "job",
    "candidate", "required", "requirements", "preferred", "experience", "skills", "years", "year",
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", text.lower())


def _extract_keywords(job_description: str, limit: int = 15) -> list[str]:
    tokens = [t for t in _tokenize(job_description) if t not in STOPWORDS]
    counts = Counter(tokens)
    ordered = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    return [word for word, _ in ordered[:limit]]


def analyze_resume_fallback(resume_text: str, job_description: str | None) -> ResumeAnalysis:
    resume_lower = resume_text.lower()
    resume_words = _tokenize(resume_text)
    jd = (job_description or "").strip()
    jd_keywords = _extract_keywords(jd)

    matched = [kw for kw in jd_keywords if kw in resume_lower]
    missing = [kw for kw in jd_keywords if kw not in resume_lower]

    has_numbers = bool(re.search(r"\b\d+(?:\.\d+)?%?\b", resume_text))
    has_sections = any(s in resume_lower for s in ["experience", "education", "projects", "skills"])

    match_ratio = (len(matched) / len(jd_keywords)) if jd_keywords else 0.6

    skills_match = int(max(20, min(100, round(40 + match_ratio * 60))))
    experience_relevance = int(max(20, min(100, round((55 if has_sections else 40) + match_ratio * 35))))
    impact_and_achievements = 75 if has_numbers else 45
    formatting_and_clarity = 78 if has_sections and len(resume_words) > 150 else 60
    overall = int(round((skills_match + experience_relevance + impact_and_achievements + formatting_and_clarity) / 4))

    strengths: list[str] = []
    gaps: list[str] = []
    suggestions: list[str] = []

    if matched:
        strengths.append(f"Resume aligns with {len(matched)} important job keywords.")
    if has_numbers:
        strengths.append("Includes quantifiable achievements, which strengthens impact.")
    if has_sections:
        strengths.append("Contains recognizable core sections for recruiter readability.")

    if not has_numbers:
        gaps.append("Limited quantified impact metrics (percentages, counts, outcomes).")
    if missing:
        gaps.append("Missing several job-specific keywords from the target description.")
    if len(resume_words) < 120:
        gaps.append("Resume content appears brief and may lack depth for evaluation.")

    suggestions.append("Add 2-3 measurable outcomes per recent role (e.g., %, time saved, revenue impact).")
    if missing:
        suggestions.append(f"Incorporate relevant terms naturally: {', '.join(missing[:8])}.")
    suggestions.append("Tailor the summary and top bullets to the exact role requirements.")

    summary = "Rule-based analysis generated because LocalAI is unavailable. "
    summary += f"Estimated fit is {overall}/100 based on keyword match, structure, and impact signals."

    return ResumeAnalysis(
        candidate_summary=summary,
        strengths=strengths or ["Resume includes baseline professional information."],
        gaps=gaps or ["No major structural issues detected by fallback analyzer."],
        suggested_improvements=suggestions,
        missing_keywords=missing[:12],
        score=ScoreBreakdown(
            overall=overall,
            skills_match=skills_match,
            experience_relevance=experience_relevance,
            impact_and_achievements=impact_and_achievements,
            formatting_and_clarity=formatting_and_clarity,
        ),
    )