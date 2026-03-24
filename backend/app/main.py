import asyncio
import json

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import settings
from app.schemas import AnalysisResponse, ResumeListItem, ResumeVersionItem
from app.services.analysis_engine import run_analysis
from app.services.localai_client import get_localai_status
from app.services.resume_parser import parse_resume_document
from app.services.versioning_store import (
    get_analysis,
    get_or_create_resume,
    init_db,
    list_resume_versions,
    list_resumes,
    save_analysis,
)


app = FastAPI(title="AI Resume Analyzer", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    init_db()


def _require_user_id(x_user_id: str | None) -> str:
    user_id = (x_user_id or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    if len(user_id) < 8 or len(user_id) > 120:
        raise HTTPException(status_code=400, detail="Invalid X-User-Id")
    return user_id


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/localai/status")
async def localai_status() -> dict:
    status = await get_localai_status()
    status["fallback_enabled"] = settings.enable_fallback_analyzer
    return status


async def _analyze_internal_from_content(
    owner_id: str,
    filename: str,
    content: bytes,
    job_description: str,
) -> AnalysisResponse:
    max_bytes = settings.max_resume_file_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum allowed size is {settings.max_resume_file_size_mb}MB.",
        )

    parsed_resume = parse_resume_document(filename, content)
    if not parsed_resume.cleaned_text:
        raise HTTPException(
            status_code=400,
            detail="No text could be extracted from this file. Try a text-based PDF, DOCX, or TXT.",
        )

    resume_id = get_or_create_resume(owner_id, filename, content)
    next_version = len(list_resume_versions(owner_id, resume_id)) + 1

    analysis_payload, engine_name, _ = await run_analysis(
        filename=filename,
        parsed_resume=parsed_resume,
        job_description=job_description or "",
        resume_id=resume_id,
        version=next_version,
    )

    analysis_id, saved_version = save_analysis(
        owner_id=owner_id,
        resume_id=resume_id,
        job_description=job_description or "",
        analysis=analysis_payload,
        engine=engine_name,
    )

    analysis_payload["meta"]["version"] = saved_version

    return AnalysisResponse(
        filename=filename,
        analysis_id=analysis_id,
        analysis=analysis_payload,
    )


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_resume(
    resume_file: UploadFile = File(...),
    job_description: str = Form(default=""),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> AnalysisResponse:
    owner_id = _require_user_id(x_user_id)
    content = await resume_file.read()
    filename = resume_file.filename or "resume.txt"
    return await _analyze_internal_from_content(owner_id, filename, content, job_description)


@app.post("/api/analyze/stream")
async def analyze_resume_stream(
    resume_file: UploadFile = File(...),
    job_description: str = Form(default=""),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> StreamingResponse:
    owner_id = _require_user_id(x_user_id)
    content = await resume_file.read()
    filename = resume_file.filename or "resume.txt"

    async def event_generator():
        try:
            yield "event: status\ndata: " + json.dumps({"stage": "ingest", "message": "Reading resume"}) + "\n\n"
            await asyncio.sleep(0.05)
            yield "event: status\ndata: " + json.dumps({"stage": "parse", "message": "Parsing sections and signals"}) + "\n\n"
            await asyncio.sleep(0.05)
            yield "event: status\ndata: " + json.dumps({"stage": "score", "message": "Calculating ATS and semantic scores"}) + "\n\n"

            result = await _analyze_internal_from_content(owner_id, filename, content, job_description)

            yield "event: status\ndata: " + json.dumps({"stage": "finalize", "message": "Preparing dashboard and suggestions"}) + "\n\n"
            yield "event: result\ndata: " + json.dumps(result.model_dump()) + "\n\n"
            yield "event: done\ndata: {}\n\n"
        except HTTPException as exc:
            yield "event: error\ndata: " + json.dumps({"detail": exc.detail, "status_code": exc.status_code}) + "\n\n"
        except Exception as exc:
            yield "event: error\ndata: " + json.dumps({"detail": str(exc), "status_code": 500}) + "\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/resumes", response_model=list[ResumeListItem])
async def get_resumes_endpoint(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> list[ResumeListItem]:
    owner_id = _require_user_id(x_user_id)
    return list_resumes(owner_id)


@app.get("/api/resumes/{resume_id}/versions", response_model=list[ResumeVersionItem])
async def get_resume_versions_endpoint(
    resume_id: str,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> list[ResumeVersionItem]:
    owner_id = _require_user_id(x_user_id)
    return list_resume_versions(owner_id, resume_id)


@app.get("/api/analysis/{analysis_id}")
async def get_analysis_detail(
    analysis_id: str,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict:
    owner_id = _require_user_id(x_user_id)
    result = get_analysis(owner_id, analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return result