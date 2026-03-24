import re
from dataclasses import dataclass
from io import BytesIO

from fastapi import HTTPException

try:
    from docx import Document
except ModuleNotFoundError:
    Document = None

try:
    from pypdf import PdfReader
except ModuleNotFoundError:
    PdfReader = None


SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}
SECTION_HEADERS = [
    "summary",
    "professional summary",
    "experience",
    "work experience",
    "employment",
    "education",
    "projects",
    "skills",
    "certifications",
    "achievements",
]


@dataclass
class ParsedResume:
    raw_text: str
    cleaned_text: str
    sections: dict[str, str]
    bullets: list[str]
    contact: dict[str, str]


def _extract_pdf_text(data: bytes) -> str:
    global PdfReader
    if PdfReader is None:
        try:
            from pypdf import PdfReader as _PdfReader
            PdfReader = _PdfReader
        except ModuleNotFoundError:
            raise HTTPException(
                status_code=500,
                detail="PDF parser dependency missing. Install backend requirements.",
            )

    reader = PdfReader(BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def _extract_docx_text(data: bytes) -> str:
    global Document
    if Document is None:
        try:
            from docx import Document as _Document
            Document = _Document
        except ModuleNotFoundError:
            raise HTTPException(
                status_code=500,
                detail="DOCX parser dependency missing (python-docx). Install backend requirements.",
            )

    document = Document(BytesIO(data))
    return "\n".join(p.text for p in document.paragraphs).strip()


def extract_resume_text(filename: str, data: bytes) -> str:
    lowered = filename.lower()

    if lowered.endswith(".txt"):
        return data.decode("utf-8", errors="ignore").strip()
    if lowered.endswith(".pdf"):
        return _extract_pdf_text(data)
    if lowered.endswith(".docx"):
        return _extract_docx_text(data)

    raise HTTPException(
        status_code=400,
        detail="Unsupported file type. Allowed types: .txt, .pdf, .docx",
    )


def _normalize_text(raw: str) -> str:
    text = raw.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _extract_sections(text: str) -> dict[str, str]:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    sections: dict[str, list[str]] = {"general": []}
    current = "general"

    for line in lines:
        lowered = line.lower().rstrip(":")
        if lowered in SECTION_HEADERS:
            current = lowered
            sections.setdefault(current, [])
            continue

        if re.fullmatch(r"[A-Z][A-Z &]{2,}", line) and len(line.split()) <= 4:
            lowered_header = line.lower().strip().rstrip(":")
            current = lowered_header
            sections.setdefault(current, [])
            continue

        sections.setdefault(current, []).append(line)

    return {k: "\n".join(v).strip() for k, v in sections.items() if v}


def _extract_bullets(text: str) -> list[str]:
    bullets = []
    for line in text.split("\n"):
        stripped = line.strip()
        if re.match(r"^[-*\u2022]\s+", stripped):
            bullets.append(re.sub(r"^[-*\u2022]\s+", "", stripped))
    return bullets


def _extract_contact(text: str) -> dict[str, str]:
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone_match = re.search(r"(?:\+?\d{1,3}[ -]?)?(?:\(?\d{3}\)?[ -]?)\d{3}[ -]?\d{4}", text)
    linkedin_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/[^\s]+", text, re.IGNORECASE)

    return {
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0) if phone_match else "",
        "linkedin": linkedin_match.group(0) if linkedin_match else "",
    }


def parse_resume_document(filename: str, data: bytes) -> ParsedResume:
    raw_text = extract_resume_text(filename, data)
    cleaned_text = _normalize_text(raw_text)
    sections = _extract_sections(cleaned_text)
    bullets = _extract_bullets(cleaned_text)
    contact = _extract_contact(cleaned_text)

    return ParsedResume(
        raw_text=raw_text,
        cleaned_text=cleaned_text,
        sections=sections,
        bullets=bullets,
        contact=contact,
    )