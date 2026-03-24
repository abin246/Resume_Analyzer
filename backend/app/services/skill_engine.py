import re
from collections import Counter


SKILL_TAXONOMY: dict[str, list[str]] = {
    "languages": ["python", "java", "javascript", "typescript", "go", "c++", "c#", "sql"],
    "frontend": ["react", "next.js", "redux", "html", "css", "tailwind", "vite"],
    "backend": ["fastapi", "django", "flask", "node.js", "express", "spring", "rest", "graphql"],
    "data": ["pandas", "numpy", "spark", "airflow", "etl", "power bi", "tableau"],
    "cloud": ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd"],
    "ai_ml": ["machine learning", "deep learning", "pytorch", "tensorflow", "llm", "nlp"],
}


def _normalize(text: str) -> str:
    return text.lower()


def extract_skills(text: str) -> list[str]:
    normalized = _normalize(text)
    found: set[str] = set()

    for skills in SKILL_TAXONOMY.values():
        for skill in skills:
            pattern = r"\b" + re.escape(skill.lower()) + r"\b"
            if re.search(pattern, normalized):
                found.add(skill)

    return sorted(found)


def extract_top_keywords(text: str, limit: int = 20) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", text.lower())
    stop = {
        "the", "and", "for", "with", "that", "this", "from", "have", "has", "you", "your", "are",
        "will", "years", "year", "experience", "required", "preferred", "team", "work", "role",
    }
    filtered = [tok for tok in tokens if tok not in stop]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(limit)]


def build_skill_match(resume_text: str, job_description: str) -> dict:
    resume_skills = extract_skills(resume_text)
    jd_skills = extract_skills(job_description)

    if not jd_skills:
        jd_skills = extract_top_keywords(job_description, limit=12)

    matched = sorted([s for s in jd_skills if s in resume_skills])
    missing = sorted([s for s in jd_skills if s not in resume_skills])
    coverage = len(matched) / len(jd_skills) if jd_skills else 0.0

    return {
        "all_resume_skills": resume_skills,
        "required_skills": jd_skills,
        "matched_skills": matched,
        "missing_skills": missing,
        "coverage_ratio": round(coverage, 4),
    }