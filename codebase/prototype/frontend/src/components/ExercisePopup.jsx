import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { createQuiz } from '../api'

export default function ExercisePopup({ documentId, sessionId, onClose }) {
  const [userRequest, setUserRequest] = useState('')
  const [numQuestions, setNumQuestions] = useState(5)
  const [questions, setQuestions] = useState(null)
  const [answers, setAnswers] = useState({})
  const [submitted, setSubmitted] = useState(false)
  const [revealedExplanations, setRevealedExplanations] = useState(new Set())
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState(null)

  async function handleGenerate() {
    setGenerating(true)
    setError(null)
    try {
      const res = await createQuiz({ documentId, sessionId, userRequest, numQuestions })
      setQuestions(res.questions)
      setAnswers({})
      setSubmitted(false)
      setRevealedExplanations(new Set())
    } catch (err) {
      setError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  function handleSelect(qIndex, optionIndex) {
    if (submitted) return
    setAnswers((prev) => ({ ...prev, [qIndex]: optionIndex }))
  }

  function toggleExplanation(qIndex) {
    setRevealedExplanations((prev) => {
      const next = new Set(prev)
      if (next.has(qIndex)) next.delete(qIndex)
      else next.add(qIndex)
      return next
    })
  }

  const answeredCount = Object.keys(answers).length
  const canSubmit = questions && answeredCount === questions.length && !submitted
  const correctCount = questions
    ? questions.reduce((acc, q, i) => acc + (answers[i] === q.correct_index ? 1 : 0), 0)
    : 0

  return (
    <div className="popup-overlay">
      <div className="popup-card">
        <button type="button" className="popup-close" onClick={onClose}>
          ×
        </button>
        <h2 className="popup-title">Bài tập trắc nghiệm</h2>
        <div className="popup-body quiz-popup-body">
          {error && <p className="error-banner">{error}</p>}

          {!questions && (
            <div className="quiz-generate-form">
              <p>Bạn muốn tập trung vào phần nào của bài giảng? (để trống = toàn bộ)</p>
              <input
                type="text"
                value={userRequest}
                onChange={(e) => setUserRequest(e.target.value)}
                placeholder="Ví dụ: overfitting và supervised learning"
              />
              <label className="quiz-num-questions">
                Số câu hỏi:
                <input
                  type="number"
                  min={1}
                  max={15}
                  value={numQuestions}
                  onChange={(e) => setNumQuestions(Number(e.target.value))}
                />
              </label>
              <button type="button" onClick={handleGenerate} disabled={generating}>
                {generating ? 'Đang tạo câu hỏi...' : 'Tạo bài tập'}
              </button>
            </div>
          )}

          {questions && (
            <>
              {submitted && (
                <div className="quiz-stats">
                  Kết quả: <strong>{correctCount}/{questions.length}</strong> câu đúng (
                  {Math.round((correctCount / questions.length) * 100)}%)
                </div>
              )}

              <div className="quiz-question-list">
                {questions.map((q, qIndex) => {
                  const selected = answers[qIndex]
                  const isCorrect = selected === q.correct_index
                  return (
                    <div
                      key={qIndex}
                      className={`quiz-question-card${submitted ? (isCorrect ? ' correct' : ' incorrect') : ''}`}
                    >
                      <p className="quiz-question-text">
                        {qIndex + 1}. {q.question}
                        {q.page_number != null && <span className="quiz-question-page"> (trang {q.page_number})</span>}
                      </p>
                      <div className="quiz-options">
                        {q.options.map((opt, optIndex) => {
                          const isSelected = selected === optIndex
                          const isRightAnswer = optIndex === q.correct_index
                          let optionClass = 'quiz-option'
                          if (submitted) {
                            if (isRightAnswer) optionClass += ' right-answer'
                            else if (isSelected) optionClass += ' wrong-answer'
                          } else if (isSelected) {
                            optionClass += ' selected'
                          }
                          return (
                            <label key={optIndex} className={optionClass}>
                              <input
                                type="radio"
                                name={`quiz-q-${qIndex}`}
                                checked={isSelected || false}
                                onChange={() => handleSelect(qIndex, optIndex)}
                                disabled={submitted}
                              />
                              {String.fromCharCode(65 + optIndex)}. {opt}
                            </label>
                          )
                        })}
                      </div>

                      {submitted && (
                        <div className="quiz-explanation-toggle">
                          <button type="button" onClick={() => toggleExplanation(qIndex)}>
                            {revealedExplanations.has(qIndex) ? 'Ẩn giải thích' : 'Giải thích'}
                          </button>
                          {revealedExplanations.has(qIndex) && (
                            <div className="quiz-explanation-text">
                              <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                                {q.explanation}
                              </ReactMarkdown>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>

              <div className="quiz-actions">
                {!submitted ? (
                  <button type="button" onClick={() => setSubmitted(true)} disabled={!canSubmit}>
                    Nộp bài ({answeredCount}/{questions.length})
                  </button>
                ) : (
                  <button type="button" onClick={() => setQuestions(null)}>
                    Tạo bộ câu hỏi mới
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
