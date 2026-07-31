import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { listExercises, createExercise } from '../api'

export default function ExercisePopup({ documentId, sessionId, pageNumber, onClose }) {
  const [exercises, setExercises] = useState([])
  const [expandedId, setExpandedId] = useState(null)
  const [newRequest, setNewRequest] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    listExercises(documentId, pageNumber, sessionId)
      .then((rows) => setExercises([...rows].reverse())) // most recent first
      .catch((err) => setError(err.message))
  }, [documentId, pageNumber, sessionId])

  async function handleCreate() {
    if (!newRequest.trim()) return
    setSubmitting(true)
    try {
      const res = await createExercise({ documentId, sessionId, pageNumber, userRequest: newRequest })
      setExercises((prev) => [
        { exercise_id: res.exercise_id, user_request: newRequest, exercise_text: res.exercise_text, created_at: '' },
        ...prev,
      ])
      setNewRequest('')
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="popup-overlay">
      <div className="popup-card">
        <button type="button" className="popup-close" onClick={onClose}>
          ×
        </button>
        <h2 className="popup-title">Bài tập - Trang {pageNumber}</h2>
        <div className="popup-body exercise-popup-body">
          {error && <p className="error-banner">{error}</p>}
          <div className="exercise-list">
            {exercises.map((ex) => {
              const isExpanded = expandedId === ex.exercise_id
              return (
                <div key={ex.exercise_id} className="exercise-card">
                  <button
                    type="button"
                    className="exercise-card-header"
                    onClick={() => setExpandedId(isExpanded ? null : ex.exercise_id)}
                  >
                    <span className={`chevron${isExpanded ? ' expanded' : ''}`}>▶</span>
                    <span className="exercise-request-title">{ex.user_request}</span>
                  </button>
                  {isExpanded && (
                    <div className="exercise-card-body">
                      <ReactMarkdown>{ex.exercise_text}</ReactMarkdown>
                    </div>
                  )}
                </div>
              )
            })}

            <div className="exercise-add-row">
              <p>Bạn muốn tập trung vào phần nào của slide này?</p>
              <input
                type="text"
                value={newRequest}
                onChange={(e) => setNewRequest(e.target.value)}
                placeholder="Ví dụ: bài tập code Python để tính margin"
              />
              <button type="button" onClick={handleCreate} disabled={submitting}>
                {submitting ? 'Đang tạo...' : 'Tạo'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
