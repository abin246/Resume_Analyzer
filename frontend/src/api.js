const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function getOrCreateUserId() {
  const key = "resume_analyzer_user_id";
  let id = localStorage.getItem(key);
  if (!id) {
    id = (crypto?.randomUUID?.() || `user-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`);
    localStorage.setItem(key, id);
  }
  return id;
}

function authHeaders() {
  return {
    "X-User-Id": getOrCreateUserId(),
  };
}

// export async function getLocalAIStatus() {
//   const response = await fetch(`${API_BASE_URL}/api/localai/status`, {
//     headers: authHeaders(),
//   });
//   if (!response.ok) throw new Error("Unable to check LocalAI status");
//   return response.json();
// }

export async function analyzeResume(file, jobDescription) {
  const formData = new FormData();
  formData.append("resume_file", file);
  formData.append("job_description", jobDescription || "");

  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to analyze resume");
  }

  return response.json();
}

export async function analyzeResumeStream(file, jobDescription, handlers = {}) {
  const formData = new FormData();
  formData.append("resume_file", file);
  formData.append("job_description", jobDescription || "");

  const response = await fetch(`${API_BASE_URL}/api/analyze/stream`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (!response.ok || !response.body) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Streaming analysis failed");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";

    for (const chunk of chunks) {
      const lines = chunk.split("\n");
      const eventLine = lines.find((l) => l.startsWith("event:"));
      const dataLine = lines.find((l) => l.startsWith("data:"));
      if (!eventLine || !dataLine) continue;

      const eventType = eventLine.replace("event:", "").trim();
      const payloadText = dataLine.replace("data:", "").trim();
      const payload = payloadText ? JSON.parse(payloadText) : {};

      if (eventType === "status" && handlers.onStatus) handlers.onStatus(payload);
      if (eventType === "result" && handlers.onResult) handlers.onResult(payload);
      if (eventType === "error") throw new Error(payload.detail || "Analysis stream failed");
      if (eventType === "done" && handlers.onDone) handlers.onDone();
    }
  }
}

export async function getResumes() {
  const response = await fetch(`${API_BASE_URL}/api/resumes`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to load resumes");
  return response.json();
}

export async function getResumeVersions(resumeId) {
  const response = await fetch(`${API_BASE_URL}/api/resumes/${resumeId}/versions`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to load resume versions");
  return response.json();
}

export async function getAnalysisById(analysisId) {
  const response = await fetch(`${API_BASE_URL}/api/analysis/${analysisId}`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to load analysis");
  return response.json();
}