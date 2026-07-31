// VITE_API_BASE overrides the default when set (e.g. a separate-service
// deploy pointing at a different domain). Unset, it defaults by build mode:
// - dev (`vite dev`): localhost:8020, since the Vite dev server (:5173) and
//   FastAPI are two separate processes here (port 8000 has a persistent
//   Windows stale-socket issue on this machine).
// - prod (`vite build`): '' (same-origin relative paths), because the
//   single-service deploy has FastAPI serve this build's static files
//   itself -- see DEPLOY.md.
export const API_BASE = import.meta.env.VITE_API_BASE ?? (import.meta.env.DEV ? 'http://localhost:8020' : '')

async function request(path, options) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${options?.method || 'GET'} ${path} failed: ${res.status} ${text}`)
  }
  return res.json()
}

export function createSession(answers) {
  return request('/session', { method: 'POST', body: JSON.stringify(answers) })
}

export function listPdfs() {
  return request('/pdfs')
}

export function ingestPdf(pdfFilename) {
  return request('/ingest', { method: 'POST', body: JSON.stringify({ pdf_filename: pdfFilename }) })
}

export function getSummary(documentId, refresh = false) {
  return request(`/summary/${documentId}${refresh ? '?refresh=true' : ''}`)
}

export function explain({ documentId, sessionId, mode, nodeId, pageNumber, selectedText, userQuestion, chatHistory }) {
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
      chat_history: chatHistory,
    }),
  })
}

export function createQuiz({ documentId, sessionId, userRequest, numQuestions }) {
  return request('/quiz', {
    method: 'POST',
    body: JSON.stringify({
      document_id: documentId,
      session_id: sessionId,
      user_request: userRequest,
      num_questions: numQuestions,
    }),
  })
}

export function pdfUrl(documentId) {
  return `${API_BASE}/pdf/${documentId}`
}
