import { useState } from 'react'
import { QUESTIONS } from '../onboardingQuestions'
import { createSession } from '../api'

export default function Onboarding({ onComplete }) {
  const [stepIndex, setStepIndex] = useState(0)
  const [answers, setAnswers] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const question = QUESTIONS[stepIndex]
  const selected = answers[question.key]
  const isLast = stepIndex === QUESTIONS.length - 1

  function selectOption(option) {
    setAnswers((prev) => ({ ...prev, [question.key]: option }))
  }

  async function goNext() {
    if (!selected) return
    if (!isLast) {
      setStepIndex((i) => i + 1)
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const { session_id } = await createSession(answers)
      onComplete(session_id)
    } catch (err) {
      setError(err.message)
      setSubmitting(false)
    }
  }

  function goBack() {
    if (stepIndex > 0) setStepIndex((i) => i - 1)
  }

  return (
    <div className="onboarding-page">
      <div className="onboarding-card">
        <div className="onboarding-progress-bar">
          {QUESTIONS.map((q, i) => (
            <div key={q.key} className={`onboarding-progress-segment${i <= stepIndex ? ' filled' : ''}`} />
          ))}
        </div>
        <p className="onboarding-progress">
          Question {stepIndex + 1}/{QUESTIONS.length}
        </p>
        <h2>{question.question}</h2>
        <div className="onboarding-options">
          {question.options.map((option) => (
            <button
              key={option}
              type="button"
              className={`onboarding-option${selected === option ? ' selected' : ''}`}
              onClick={() => selectOption(option)}
            >
              {option}
            </button>
          ))}
        </div>
        {error && <p className="onboarding-error">{error}</p>}
        <div className="onboarding-nav">
          <button type="button" onClick={goBack} disabled={stepIndex === 0}>
            Quay lại
          </button>
          <button type="button" onClick={goNext} disabled={!selected || submitting}>
            {isLast ? (submitting ? 'Đang gửi...' : 'Hoàn thành') : 'Tiếp theo'}
          </button>
        </div>
      </div>
    </div>
  )
}
