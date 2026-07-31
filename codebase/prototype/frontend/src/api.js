export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8020'

async function request(path, options) {
  const headers = { ...(options?.headers || {}) }
  if (options?.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })
  if (!res.ok) {
    const payload = await res.json().catch(() => null)
    const detail = payload?.detail?.message || payload?.detail || `HTTP ${res.status}`
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return res.json()
}

export function createSession(answers) {
  return request('/session', { method: 'POST', body: JSON.stringify(answers) })
}

export function ingestPdf(pdfFilename) {
  return request('/ingest', { method: 'POST', body: JSON.stringify({ pdf_filename: pdfFilename }) })
}

export function listDocuments() {
  return request('/documents')
}

export function getIngestStatus(jobId) {
  return request(`/ingest/status/${jobId}`)
}

export function getSummary(documentId) {
  return request(`/summary/${documentId}`)
}

export function explain({ documentId, sessionId, mode, nodeId, pageNumber, selectedText, userQuestion }) {
  return request('/explain', {
    method: 'POST',
    body: JSON.stringify({
      document_id: documentId,
      session_id: sessionId,
      mode,
      node_id: nodeId,
      page_number: pageNumber,
      selected_text: selectedText,
      user_question: userQuestion,
    }),
  })
}

export function createExercise({ documentId, sessionId, pageNumber, userRequest }) {
  return request('/exercise', {
    method: 'POST',
    body: JSON.stringify({
      document_id: documentId,
      session_id: sessionId,
      page_number: pageNumber,
      user_request: userRequest,
    }),
  })
}

export function listExercises(documentId, pageNumber, sessionId) {
  return request(`/exercises/${documentId}/${pageNumber}?session_id=${sessionId}`)
}

export function pdfUrl(documentId) {
  return `${API_BASE}/pdf/${documentId}`
}
