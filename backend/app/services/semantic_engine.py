import math
import re
from collections import Counter


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", text.lower())


def _tf(tokens: list[str]) -> Counter:
    return Counter(tokens)


def _cosine(counter_a: Counter, counter_b: Counter) -> float:
    if not counter_a or not counter_b:
        return 0.0

    intersection = set(counter_a) & set(counter_b)
    numerator = sum(counter_a[t] * counter_b[t] for t in intersection)

    norm_a = math.sqrt(sum(v * v for v in counter_a.values()))
    norm_b = math.sqrt(sum(v * v for v in counter_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0

    return numerator / (norm_a * norm_b)


def compute_semantic_alignment(resume_sections: dict[str, str], job_description: str) -> dict:
    jd_tokens = _tokenize(job_description)
    jd_tf = _tf(jd_tokens)

    section_matches = []
    section_scores = []

    for section, content in resume_sections.items():
        tokens = _tokenize(content)
        section_tf = _tf(tokens)
        similarity = _cosine(section_tf, jd_tf)
        common_terms = sorted(list((set(tokens) & set(jd_tokens))))[:10]

        section_matches.append(
            {
                "section": section,
                "similarity": round(float(similarity), 4),
                "evidence_terms": common_terms,
            }
        )
        section_scores.append(similarity)

    overall = sum(section_scores) / len(section_scores) if section_scores else 0.0

    return {
        "overall_similarity": round(float(overall), 4),
        "section_matches": sorted(section_matches, key=lambda x: x["similarity"], reverse=True),
    }