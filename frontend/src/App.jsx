import { useEffect, useMemo, useState } from "react";
import {
  analyzeResumeStream,
  getAnalysisById,
  getLocalAIStatus,
  getResumeVersions,
  getResumes,
} from "./api";

const ACCEPTED_TYPES = ".pdf,.docx,.txt";

function ScoreBar({ label, value }) {
  return (
    <div className="score-row">
      <div className="score-label">
        <span>{label}</span>
        <strong>{value}/100</strong>
      </div>
      <div className="score-track">
        <div className="score-fill" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <article className="stat-card">
      <p>{label}</p>
      <h3>{value}</h3>
    </article>
  );
}

function SectionList({ title, items }) {
  return (
    <section className="analysis-card">
      <h3>{title}</h3>
      {items?.length ? (
        <ul>
          {items.map((item, index) => (
            <li key={`${title}-${index}`}>{typeof item === "string" ? item : JSON.stringify(item)}</li>
          ))}
        </ul>
      ) : (
        <p className="muted">No items detected.</p>
      )}
    </section>
  );
}

function RewriteList({ items }) {
  return (
    <section className="analysis-card summary-card">
      <h3>Resume Rewrite Suggestions (High Value)</h3>
      {items?.length ? (
        <div className="rewrite-grid">
          {items.map((row, idx) => (
            <article key={`rewrite-${idx}`} className="rewrite-item">
              <p className="rewrite-meta">Section: {row.section}</p>
              <p><strong>Before:</strong> {row.original}</p>
              <p><strong>After:</strong> {row.improved}</p>
              <p className="muted">Why: {row.reason}</p>
            </article>
          ))}
        </div>
      ) : (
        <p className="muted">No rewrite suggestions yet.</p>
      )}
    </section>
  );
}

export default function App() {
  const [file, setFile] = useState(null);
  const [jobDescription, setJobDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [localaiStatus, setLocalaiStatus] = useState(null);
  const [streamStage, setStreamStage] = useState("");

  const [resumeList, setResumeList] = useState([]);
  const [selectedResumeId, setSelectedResumeId] = useState("");
  const [versions, setVersions] = useState([]);

  async function refreshResumes() {
    try {
      const items = await getResumes();
      setResumeList(items);
      if (!selectedResumeId && items.length) {
        setSelectedResumeId(items[0].resume_id);
      }
    } catch {
      // Keep non-blocking
    }
  }

  useEffect(() => {
    let active = true;

    async function fetchStatus() {
      try {
        const status = await getLocalAIStatus();
        if (active) setLocalaiStatus(status);
      } catch {
        if (active) {
          setLocalaiStatus({ reachable: false, message: "Unable to check LocalAI status." });
        }
      }
    }

    fetchStatus();
    refreshResumes();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    async function loadVersions() {
      if (!selectedResumeId) {
        setVersions([]);
        return;
      }
      try {
        const list = await getResumeVersions(selectedResumeId);
        setVersions(list);
      } catch {
        setVersions([]);
      }
    }
    loadVersions();
  }, [selectedResumeId]);

  const isSubmitDisabled = useMemo(() => !file || loading, [file, loading]);

  async function onSubmit(event) {
    event.preventDefault();
    if (!file) {
      setError("Please upload a resume file first.");
      return;
    }

    setLoading(true);
    setError("");
    setStreamStage("Initializing analysis pipeline...");

    try {
      await analyzeResumeStream(file, jobDescription, {
        onStatus: (status) => setStreamStage(status.message || status.stage),
        onResult: (payload) => setResult(payload),
        onDone: () => setStreamStage("Analysis complete"),
      });
      await refreshResumes();
    } catch (err) {
      setResult(null);
      setError(err.message || "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  async function openVersion(analysisId) {
    try {
      const payload = await getAnalysisById(analysisId);
      setResult({
        analysis_id: payload.analysis_id,
        filename: resumeList.find((r) => r.resume_id === payload.resume_id)?.filename || "resume",
        analysis: payload.analysis,
      });
    } catch (err) {
      setError(err.message || "Unable to open saved version");
    }
  }

  return (
    <div className="page">
      <div className="background-glow" aria-hidden="true" />
      <main className="container">
        <header className="hero">
          <p className="eyebrow">Enterprise-grade ATS + semantic intelligence</p>
          <h1>AI Resume Analyzer Pro</h1>
          <p>
            ATS matching, structured AI output, trustworthy scoring, semantic analysis, rewrite
            intelligence, streaming feedback, and version tracking in one workflow.
          </p>
        </header>

        {localaiStatus ? (
          <section className={`panel ${localaiStatus.reachable ? "status-ok" : "status-bad"}`}>
            <p className="status-title">LocalAI: {localaiStatus.reachable ? "Connected" : "Offline"}</p>
            <p className="muted">
              {localaiStatus.reachable
                ? `Model endpoint active at ${localaiStatus.base_url}`
                : "Fallback deterministic engine is active. You can still run full ATS analysis."}
            </p>
          </section>
        ) : null}

        <section className="panel two-col">
          <form onSubmit={onSubmit} className="form">
            <label className="field">
              <span>Resume file</span>
              <input
                type="file"
                accept={ACCEPTED_TYPES}
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </label>

            <label className="field">
              <span>Target job description</span>
              <textarea
                rows={8}
                placeholder="Paste role requirements, responsibilities, and must-have skills..."
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
              />
            </label>

            <button type="submit" disabled={isSubmitDisabled}>
              {loading ? "Analyzing..." : "Run ATS + Semantic Analysis"}
            </button>

            {streamStage ? <p className="stream-status">Live: {streamStage}</p> : null}
            {error ? <p className="error">{error}</p> : null}
          </form>

          <aside className="version-panel">
            <h3>Resume Versioning</h3>
            <label className="field">
              <span>Saved resumes</span>
              <select
                value={selectedResumeId}
                onChange={(e) => setSelectedResumeId(e.target.value)}
              >
                <option value="">Select resume</option>
                {resumeList.map((item) => (
                  <option key={item.resume_id} value={item.resume_id}>
                    {item.filename} (v{item.latest_version})
                  </option>
                ))}
              </select>
            </label>

            <div className="version-list">
              {versions.map((v) => (
                <button key={v.analysis_id} className="version-item" onClick={() => openVersion(v.analysis_id)} type="button">
                  v{v.version} | Score {v.overall_score}
                </button>
              ))}
            </div>
          </aside>
        </section>

        {result ? (
          <>
            <section className="stats-grid">
              <StatCard label="Overall Match" value={`${result.analysis.score.overall}/100`} />
              <StatCard label="ATS Match" value={`${result.analysis.score.ats_match}/100`} />
              <StatCard label="Semantic Match" value={`${result.analysis.score.semantic_match}/100`} />
              <StatCard label="Confidence" value={`${result.analysis.meta.confidence}%`} />
            </section>

            <section className="analysis-card summary-card">
              <h2>Structured AI Output</h2>
              <p>{result.analysis.candidate_summary}</p>
              <p className="muted">
                Recommendation: {result.analysis.ats_recommendation} | Engine: {result.analysis.meta.engine}
              </p>
            </section>

            <section className="result-grid">
              <article className="analysis-card">
                <h2>Trustworthy Scoring</h2>
                <ScoreBar label="Overall" value={result.analysis.score.overall} />
                <ScoreBar label="ATS Match" value={result.analysis.score.ats_match} />
                <ScoreBar label="Semantic Match" value={result.analysis.score.semantic_match} />
                <ScoreBar label="Skill Coverage" value={result.analysis.score.skill_coverage} />
                <ScoreBar label="Experience Relevance" value={result.analysis.score.experience_relevance} />
                <ScoreBar label="Impact" value={result.analysis.score.impact_and_achievements} />
                <ScoreBar label="Formatting" value={result.analysis.score.formatting_and_clarity} />
              </article>

              <article className="analysis-card">
                <h2>Visual Dashboard</h2>
                <ScoreBar label="Gauge Match" value={result.analysis.dashboard.match_gauge} />
                <ScoreBar label="Keyword Coverage" value={result.analysis.dashboard.keyword_coverage} />
                <ScoreBar label="Semantic Alignment" value={result.analysis.dashboard.semantic_alignment} />
                <ScoreBar label="Impact Density" value={result.analysis.dashboard.impact_density} />
              </article>

              <SectionList title="Strengths" items={result.analysis.strengths} />
              <SectionList title="Gaps" items={result.analysis.gaps} />
              <SectionList title="Suggested Improvements" items={result.analysis.suggested_improvements} />
              <SectionList title="Missing Keywords" items={result.analysis.missing_keywords} />
            </section>

            <section className="analysis-card">
              <h3>Skill Extraction Engine</h3>
              <p className="muted">
                Required: {result.analysis.skill_extraction.required_skills.join(", ") || "None detected"}
              </p>
              <p className="muted">
                Matched: {result.analysis.skill_extraction.matched_skills.join(", ") || "None"}
              </p>
              <p className="muted">
                Missing: {result.analysis.skill_extraction.missing_skills.join(", ") || "None"}
              </p>
            </section>

            <section className="analysis-card">
              <h3>Semantic Matching (Advanced)</h3>
              <div className="semantic-grid">
                {result.analysis.semantic_matches.map((m, idx) => (
                  <article key={`semantic-${idx}`} className="semantic-item">
                    <p><strong>{m.section}</strong></p>
                    <p>Similarity: {Math.round((m.similarity || 0) * 100)}%</p>
                    <p className="muted">Evidence: {(m.evidence_terms || []).join(", ") || "-"}</p>
                  </article>
                ))}
              </div>
            </section>

            <RewriteList items={result.analysis.rewrite_suggestions} />

            <section className="analysis-card summary-card">
              <h3>Scoring Evidence (Audit Trail)</h3>
              <ul>
                {result.analysis.scoring_evidence.map((e, idx) => (
                  <li key={`evidence-${idx}`}>
                    <strong>{e.metric}</strong>: {e.score}/100 (weight {Math.round(e.weight * 100)}%) - {e.rationale}
                  </li>
                ))}
              </ul>
            </section>
          </>
        ) : null}
      </main>
    </div>
  );
}