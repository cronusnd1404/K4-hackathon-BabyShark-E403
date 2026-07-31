import { useState } from 'react'
import ReactMarkdown from 'react-markdown'

function truncate(text, max = 80) {
  return text.length > max ? `${text.slice(0, max)}...` : text
}

export default function ChatboxPanel({ history, pendingSelection, loading, onExplainPending, onRelatedPageClick }) {
  const [userQuestion, setUserQuestion] = useState('')

  async function handleExplainClick() {
    await onExplainPending(userQuestion)
    setUserQuestion('')
  }

  return (
    <div className="chatbox-panel">
      <div className="chatbox-history">
        {history.length === 0 && <p className="chatbox-empty">Chưa có giải thích nào.</p>}
        {history.map((entry) => (
          <div key={entry.id} className="chatbox-entry">
            <p className="chatbox-entry-label">{entry.label}</p>
            <div className="chatbox-entry-explanation">
              <ReactMarkdown>{entry.explanation}</ReactMarkdown>
            </div>
            {entry.relatedPages.length > 0 && (
              <div className="chatbox-related-pages">
                {entry.relatedPages.map((rp, i) => (
                  <button
                    key={i}
                    type="button"
                    className="related-page-chip"
                    title={rp.reason}
                    onClick={() => onRelatedPageClick(rp.page_number)}
                  >
                    Trang {rp.page_number}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {pendingSelection && (
        <div className="chatbox-pending">
          <p className="chatbox-pending-preview">
            Selected on page {pendingSelection.pageNumber}: "{truncate(pendingSelection.selectedText)}"
          </p>
          <input
            type="text"
            placeholder="Câu hỏi thêm (tuỳ chọn)..."
            value={userQuestion}
            onChange={(e) => setUserQuestion(e.target.value)}
          />
          <button type="button" onClick={handleExplainClick} disabled={loading}>
            {loading ? 'Đang giải thích...' : 'Explain'}
          </button>
        </div>
      )}
    </div>
  )
}
