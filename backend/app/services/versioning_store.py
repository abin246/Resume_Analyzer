import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS resumes (
                resume_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                analysis_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                resume_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                job_hash TEXT NOT NULL,
                overall_score INTEGER NOT NULL,
                engine TEXT NOT NULL,
                analysis_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (resume_id) REFERENCES resumes(resume_id)
            )
            """
        )

        if not _has_column(conn, "resumes", "owner_id"):
            conn.execute("ALTER TABLE resumes ADD COLUMN owner_id TEXT DEFAULT 'legacy'")
        if not _has_column(conn, "analyses", "owner_id"):
            conn.execute("ALTER TABLE analyses ADD COLUMN owner_id TEXT DEFAULT 'legacy'")
            conn.execute(
                """
                UPDATE analyses
                SET owner_id = COALESCE(
                    (SELECT r.owner_id FROM resumes r WHERE r.resume_id = analyses.resume_id),
                    'legacy'
                )
                """
            )

        conn.execute("CREATE INDEX IF NOT EXISTS idx_resumes_owner_id ON resumes(owner_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_owner_id ON analyses(owner_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_resume_id ON analyses(resume_id)")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_or_create_resume(owner_id: str, filename: str, file_content: bytes) -> str:
    file_hash = hashlib.sha256(file_content).hexdigest()

    with _connect() as conn:
        row = conn.execute(
            "SELECT resume_id FROM resumes WHERE owner_id = ? AND filename = ? AND file_hash = ?",
            (owner_id, filename, file_hash),
        ).fetchone()
        if row:
            return str(row["resume_id"])

        resume_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO resumes (resume_id, owner_id, filename, file_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (resume_id, owner_id, filename, file_hash, _utc_now()),
        )
        return resume_id


def save_analysis(owner_id: str, resume_id: str, job_description: str, analysis: dict, engine: str) -> tuple[str, int]:
    job_hash = _sha256(job_description or "")
    overall = int(analysis["score"]["overall"])

    with _connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(version), 0) AS max_version FROM analyses WHERE owner_id = ? AND resume_id = ?",
            (owner_id, resume_id),
        ).fetchone()
        version = int(row["max_version"]) + 1

        analysis_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO analyses (
                analysis_id, owner_id, resume_id, version, job_hash, overall_score, engine, analysis_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis_id,
                owner_id,
                resume_id,
                version,
                job_hash,
                overall,
                engine,
                json.dumps(analysis),
                _utc_now(),
            ),
        )

        return analysis_id, version


def list_resumes(owner_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                r.resume_id,
                r.filename,
                MAX(a.version) AS latest_version,
                COALESCE((
                    SELECT a2.overall_score
                    FROM analyses a2
                    WHERE a2.owner_id = r.owner_id AND a2.resume_id = r.resume_id
                    ORDER BY a2.version DESC
                    LIMIT 1
                ), 0) AS latest_overall_score,
                COALESCE((
                    SELECT a3.created_at
                    FROM analyses a3
                    WHERE a3.owner_id = r.owner_id AND a3.resume_id = r.resume_id
                    ORDER BY a3.version DESC
                    LIMIT 1
                ), r.created_at) AS updated_at
            FROM resumes r
            LEFT JOIN analyses a ON a.owner_id = r.owner_id AND a.resume_id = r.resume_id
            WHERE r.owner_id = ?
            GROUP BY r.resume_id, r.filename
            ORDER BY updated_at DESC
            """,
            (owner_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def list_resume_versions(owner_id: str, resume_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT analysis_id, version, overall_score, created_at
            FROM analyses
            WHERE owner_id = ? AND resume_id = ?
            ORDER BY version DESC
            """,
            (owner_id, resume_id),
        ).fetchall()

    return [dict(row) for row in rows]


def get_analysis(owner_id: str, analysis_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT analysis_id, resume_id, version, analysis_json
            FROM analyses
            WHERE owner_id = ? AND analysis_id = ?
            """,
            (owner_id, analysis_id),
        ).fetchone()

    if not row:
        return None

    payload = json.loads(row["analysis_json"])
    return {
        "analysis_id": row["analysis_id"],
        "resume_id": row["resume_id"],
        "version": row["version"],
        "analysis": payload,
    }