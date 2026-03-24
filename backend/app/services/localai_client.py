import asyncio
import json
import time
from typing import Any

import httpx
from fastapi import HTTPException

from app.config import settings


SYSTEM_PROMPT = """
You are a senior ATS resume strategist.
Return strict JSON only.
Keep suggestions practical and specific.
""".strip()

_CACHE_TTL_SECONDS = 60
_cached_base_url: str | None = None
_cached_base_time: float = 0.0


def _extract_json_content(raw_content: str) -> dict:
    cleaned = raw_content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


def _normalize_base_candidates(raw_base: str) -> list[str]:
    base = raw_base.strip().rstrip("/") or "http://127.0.0.1:8080"
    candidates: list[str] = []

    def add(url: str) -> None:
        u = url.rstrip("/")
        if u and u not in candidates:
            candidates.append(u)

    add(base)
    add(base[:-3] if base.endswith("/v1") else f"{base}/v1")

    if "127.0.0.1" in base:
        add(base.replace("127.0.0.1", "localhost"))
    if "localhost" in base:
        add(base.replace("localhost", "127.0.0.1"))

    for extra in [
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8080/v1",
        "http://localhost:8080",
        "http://localhost:8080/v1",
        "http://127.0.0.1:8081",
        "http://127.0.0.1:8081/v1",
    ]:
        add(extra)

    return candidates


async def _probe_models(client: httpx.AsyncClient, base: str) -> tuple[str, bool, list[str]]:
    try:
        response = await client.get(f"{base}/models")
        response.raise_for_status()
        payload = response.json() if response.content else {}
        model_items = payload.get("data", []) if isinstance(payload, dict) else []
        model_ids = [m.get("id", "") for m in model_items if isinstance(m, dict)]
        return base, True, model_ids
    except httpx.HTTPError:
        return base, False, []


def _cached_url() -> str | None:
    if _cached_base_url and (time.monotonic() - _cached_base_time) < _CACHE_TTL_SECONDS:
        return _cached_base_url
    return None


def _set_cached_url(url: str) -> None:
    global _cached_base_url, _cached_base_time
    _cached_base_url = url
    _cached_base_time = time.monotonic()


def _clear_cached_url() -> None:
    global _cached_base_url, _cached_base_time
    _cached_base_url = None
    _cached_base_time = 0.0


async def get_localai_status() -> dict[str, Any]:
    cached = _cached_url()
    if cached:
        return {
            "reachable": True,
            "base_url": cached,
            "checked": [f"{cached}/models"],
            "models": [],
            "cached": True,
        }

    candidates = _normalize_base_candidates(settings.localai_base_url)
    checked = [f"{b}/models" for b in candidates]
    timeout = httpx.Timeout(connect=1.0, read=1.5, write=3.0, pool=3.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        probes = await asyncio.gather(*[_probe_models(client, base) for base in candidates])

    for base, ok, models in probes:
        if ok:
            _set_cached_url(base)
            return {
                "reachable": True,
                "base_url": base,
                "checked": checked,
                "models": models,
                "cached": False,
            }

    return {
        "reachable": False,
        "checked": checked,
        "message": (
            "Cannot connect to LocalAI. Start LocalAI locally and set LOCALAI_BASE_URL in backend/.env "
            "to the actual host/port (example: http://127.0.0.1:8080)."
        ),
    }


async def _pick_working_base_url() -> str:
    status = await get_localai_status()
    if status.get("reachable"):
        return str(status["base_url"])
    raise HTTPException(status_code=503, detail="LocalAI service unavailable")


async def _chat_completion(base_url: str, payload: dict) -> httpx.Response:
    async with httpx.AsyncClient(timeout=90) as client:
        return await client.post(f"{base_url}/chat/completions", json=payload)


async def generate_ai_enhancements(context: dict[str, Any]) -> dict[str, Any]:
    base_url = await _pick_working_base_url()

    prompt = f"""
Create structured, recruiter-grade output for this analysis context.

Context:
{json.dumps(context, ensure_ascii=False)}

Return only JSON schema:
{{
  "candidate_summary": "string",
  "ats_recommendation": "Strong Match|Moderate Match|Low Match",
  "strengths": ["string"],
  "gaps": ["string"],
  "suggested_improvements": ["string"],
  "rewrite_suggestions": [
    {{"section": "string", "original": "string", "improved": "string", "reason": "string"}}
  ]
}}
""".strip()

    payload = {
        "model": settings.localai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    try:
        response = await _chat_completion(base_url, payload)
        if response.status_code >= 400:
            fallback_payload = dict(payload)
            fallback_payload.pop("response_format", None)
            response = await _chat_completion(base_url, fallback_payload)
            response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        parsed = _extract_json_content(content)
        return parsed if isinstance(parsed, dict) else {}
    except httpx.HTTPError as exc:
        _clear_cached_url()
        raise HTTPException(status_code=503, detail="LocalAI service unavailable") from exc
    except Exception:
        return {}