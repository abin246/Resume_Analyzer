from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    overall: int = Field(ge=0, le=100)
    ats_match: int = Field(ge=0, le=100)
    semantic_match: int = Field(ge=0, le=100)
    skill_coverage: int = Field(ge=0, le=100)
    experience_relevance: int = Field(ge=0, le=100)
    impact_and_achievements: int = Field(ge=0, le=100)
    formatting_and_clarity: int = Field(ge=0, le=100)


class SkillExtraction(BaseModel):
    all_resume_skills: list[str]
    required_skills: list[str]
    matched_skills: list[str]
    missing_skills: list[str]
    coverage_ratio: float = Field(ge=0, le=1)


class SemanticMatchItem(BaseModel):
    section: str
    similarity: float = Field(ge=0, le=1)
    evidence_terms: list[str]


class ScoringEvidenceItem(BaseModel):
    metric: str
    score: int = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    rationale: str


class RewriteSuggestion(BaseModel):
    section: str
    original: str
    improved: str
    reason: str


class DashboardMetrics(BaseModel):
    radar: dict[str, int]
    match_gauge: int = Field(ge=0, le=100)
    keyword_coverage: int = Field(ge=0, le=100)
    semantic_alignment: int = Field(ge=0, le=100)
    impact_density: int = Field(ge=0, le=100)


class ResumeMeta(BaseModel):
    engine: str
    model_used: str
    fallback_used: bool
    confidence: int = Field(ge=0, le=100)
    resume_id: str
    version: int = Field(ge=1)


class ResumeAnalysis(BaseModel):
    candidate_summary: str
    ats_recommendation: str
    strengths: list[str]
    gaps: list[str]
    suggested_improvements: list[str]
    missing_keywords: list[str]
    skill_extraction: SkillExtraction
    semantic_matches: list[SemanticMatchItem]
    rewrite_suggestions: list[RewriteSuggestion]
    score: ScoreBreakdown
    scoring_evidence: list[ScoringEvidenceItem]
    dashboard: DashboardMetrics
    meta: ResumeMeta


class AnalysisResponse(BaseModel):
    filename: str
    analysis_id: str
    analysis: ResumeAnalysis


class ResumeVersionItem(BaseModel):
    analysis_id: str
    version: int
    overall_score: int
    created_at: str


class ResumeListItem(BaseModel):
    resume_id: str
    filename: str
    latest_version: int
    latest_overall_score: int
    updated_at: str