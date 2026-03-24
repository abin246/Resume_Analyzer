import re


def _clamp(val: float, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, round(val))))


def compute_trustworthy_scores(
    resume_text: str,
    sections: dict[str, str],
    skill_coverage_ratio: float,
    semantic_similarity: float,
) -> dict:
    words = resume_text.split()
    word_count = len(words)
    number_count = len(re.findall(r"\b\d+(?:\.\d+)?%?\b", resume_text))

    has_experience = any(k in sections for k in ["experience", "work experience", "employment"])
    has_education = "education" in sections
    has_projects = "projects" in sections
    has_skills = "skills" in sections

    formatting_quality = _clamp(35 + 15 * has_experience + 10 * has_education + 10 * has_projects + 10 * has_skills)
    impact_density = _clamp((number_count / max(word_count, 1)) * 1800)
    skill_coverage = _clamp(skill_coverage_ratio * 100)
    semantic_match = _clamp(semantic_similarity * 100)
    experience_relevance = _clamp(45 + (20 if has_experience else 0) + semantic_similarity * 30)

    ats_match = _clamp(0.45 * skill_coverage + 0.35 * semantic_match + 0.20 * formatting_quality)

    weights = {
        "ats_match": 0.25,
        "semantic_match": 0.20,
        "skill_coverage": 0.20,
        "experience_relevance": 0.15,
        "impact_and_achievements": 0.10,
        "formatting_and_clarity": 0.10,
    }

    overall = _clamp(
        ats_match * weights["ats_match"]
        + semantic_match * weights["semantic_match"]
        + skill_coverage * weights["skill_coverage"]
        + experience_relevance * weights["experience_relevance"]
        + impact_density * weights["impact_and_achievements"]
        + formatting_quality * weights["formatting_and_clarity"]
    )

    evidence = [
        {
            "metric": "ATS Match",
            "score": ats_match,
            "weight": weights["ats_match"],
            "rationale": "Weighted blend of skill coverage, semantic alignment, and resume format.",
        },
        {
            "metric": "Semantic Match",
            "score": semantic_match,
            "weight": weights["semantic_match"],
            "rationale": "Cosine similarity between resume sections and job description terms.",
        },
        {
            "metric": "Skill Coverage",
            "score": skill_coverage,
            "weight": weights["skill_coverage"],
            "rationale": "Fraction of required role skills detected in the resume.",
        },
        {
            "metric": "Experience Relevance",
            "score": experience_relevance,
            "weight": weights["experience_relevance"],
            "rationale": "Section completeness with experience-heavy weighting and JD overlap.",
        },
        {
            "metric": "Impact & Achievements",
            "score": impact_density,
            "weight": weights["impact_and_achievements"],
            "rationale": "Density of quantified impact statements across resume content.",
        },
        {
            "metric": "Formatting & Clarity",
            "score": formatting_quality,
            "weight": weights["formatting_and_clarity"],
            "rationale": "Presence of standard ATS-friendly sections and structural signals.",
        },
    ]

    confidence = _clamp(40 + (min(word_count, 900) / 900) * 30 + (10 if has_experience else 0) + (10 if has_skills else 0) + (10 if semantic_similarity > 0.2 else 0))

    return {
        "score": {
            "overall": overall,
            "ats_match": ats_match,
            "semantic_match": semantic_match,
            "skill_coverage": skill_coverage,
            "experience_relevance": experience_relevance,
            "impact_and_achievements": impact_density,
            "formatting_and_clarity": formatting_quality,
        },
        "evidence": evidence,
        "confidence": confidence,
        "dashboard": {
            "radar": {
                "ATS": ats_match,
                "Semantic": semantic_match,
                "Skills": skill_coverage,
                "Experience": experience_relevance,
                "Impact": impact_density,
                "Format": formatting_quality,
            },
            "match_gauge": overall,
            "keyword_coverage": skill_coverage,
            "semantic_alignment": semantic_match,
            "impact_density": impact_density,
        },
    }