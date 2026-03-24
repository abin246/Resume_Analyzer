from typing import Any

from app.config import settings
from app.schemas import ResumeAnalysis
from app.services.localai_client import generate_ai_enhancements, get_localai_status
from app.services.resume_parser import ParsedResume
from app.services.scoring_engine import compute_trustworthy_scores
from app.services.semantic_engine import compute_semantic_alignment
from app.services.skill_engine import build_skill_match, extract_top_keywords


def _default_narrative(score: int) -> tuple[str, str]:
    if score >= 80:
        return (
            "Strong profile with high ATS compatibility and competitive role alignment.",
            "Strong Match",
        )
    if score >= 60:
        return (
            "Promising profile with moderate alignment; targeted edits can raise interview likelihood.",
            "Moderate Match",
        )
    return (
        "Current profile shows low alignment with role requirements and needs focused optimization.",
        "Low Match",
    )


def _fallback_rewrites(parsed_resume: ParsedResume, missing_keywords: list[str]) -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []

    for bullet in parsed_resume.bullets[:4]:
        improved = bullet
        if missing_keywords:
            improved = f"{bullet} | Tools: {', '.join(missing_keywords[:3])}"
        suggestions.append(
            {
                "section": "experience",
                "original": bullet,
                "improved": improved,
                "reason": "Adds role-aligned keywords and improves ATS keyword traceability.",
            }
        )

    if not suggestions:
        suggestions.append(
            {
                "section": "summary",
                "original": "Professional summary is generic.",
                "improved": "Results-driven professional with measurable impact and direct alignment to the target role.",
                "reason": "A tighter summary improves recruiter scan speed and role fit clarity.",
            }
        )

    return suggestions


async def run_analysis(
    filename: str,
    parsed_resume: ParsedResume,
    job_description: str,
    resume_id: str,
    version: int,
) -> tuple[dict[str, Any], str, bool]:
    skill_match = build_skill_match(parsed_resume.cleaned_text, job_description)
    semantic = compute_semantic_alignment(parsed_resume.sections, job_description)
    scoring = compute_trustworthy_scores(
        parsed_resume.cleaned_text,
        parsed_resume.sections,
        skill_match["coverage_ratio"],
        semantic["overall_similarity"],
    )

    jd_keywords = extract_top_keywords(job_description, limit=18)
    missing_keywords = [k for k in jd_keywords if k not in parsed_resume.cleaned_text.lower()][:15]

    summary, recommendation = _default_narrative(scoring["score"]["overall"])

    base = {
        "candidate_summary": summary,
        "ats_recommendation": recommendation,
        "strengths": [
            f"Matched {len(skill_match['matched_skills'])} required skills.",
            f"Semantic alignment score is {scoring['score']['semantic_match']}/100.",
            "Deterministic weighted ATS scoring improves auditability and consistency.",
        ],
        "gaps": [
            "Missing several role-specific keywords and tools.",
            "Resume bullets can better quantify business impact.",
        ],
        "suggested_improvements": [
            "Rewrite top 4 bullets with quantified outcomes and stack terms.",
            "Add a skills matrix aligned to required job terms.",
            "Tailor summary and recent experience to this specific role.",
        ],
        "missing_keywords": missing_keywords,
        "skill_extraction": skill_match,
        "semantic_matches": semantic["section_matches"][:8],
        "rewrite_suggestions": _fallback_rewrites(parsed_resume, missing_keywords),
        "score": scoring["score"],
        "scoring_evidence": scoring["evidence"],
        "dashboard": scoring["dashboard"],
        "meta": {
            "engine": "deterministic-ats-v2",
            "model_used": "none",
            "fallback_used": True,
            "confidence": scoring["confidence"],
            "resume_id": resume_id,
            "version": version,
        },
    }

    engine_name = "deterministic-fallback"
    fallback_used = True

    try:
        status = await get_localai_status()
        if status.get("reachable"):
            context = {
                "filename": filename,
                "job_description": job_description,
                "score": base["score"],
                "missing_keywords": missing_keywords,
                "matched_skills": skill_match["matched_skills"],
                "missing_skills": skill_match["missing_skills"],
                "semantic_matches": base["semantic_matches"],
                "top_resume_bullets": parsed_resume.bullets[:6],
            }
            ai = await generate_ai_enhancements(context)
            if ai:
                base["candidate_summary"] = ai.get("candidate_summary", base["candidate_summary"])
                base["ats_recommendation"] = ai.get("ats_recommendation", base["ats_recommendation"])
                base["strengths"] = ai.get("strengths", base["strengths"])[:8]
                base["gaps"] = ai.get("gaps", base["gaps"])[:8]
                base["suggested_improvements"] = ai.get("suggested_improvements", base["suggested_improvements"])[:10]
                ai_rewrites = ai.get("rewrite_suggestions")
                if isinstance(ai_rewrites, list) and ai_rewrites:
                    base["rewrite_suggestions"] = ai_rewrites[:8]

                base["meta"]["engine"] = "hybrid-ats-localai-v3"
                base["meta"]["model_used"] = settings.localai_model
                base["meta"]["fallback_used"] = False
                engine_name = "hybrid-localai"
                fallback_used = False
    except Exception:
        pass

    validated = ResumeAnalysis.model_validate(base)
    return validated.model_dump(), engine_name, fallback_used