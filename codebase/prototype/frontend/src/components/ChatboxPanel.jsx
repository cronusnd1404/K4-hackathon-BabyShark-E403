import { useCallback, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'

function truncate(text, max = 80) {
  return text.length > max ? `${text.slice(0, max)}...` : text
}

const MIN_WIDTH = 240
const MAX_WIDTH = 640

export default function ChatboxPanel({
  history,
  pendingSelection,
  loading,
  onExplainPending,
  onAskFreeform,
  onClearPending,
  onRelatedPageClick,
}) {
  const [userQuestion, setUserQuestion] = useState('')
  const [width, setWidth] = useState(320)
  const draggingRef = useRef(false)

  const handleResizeStart = useCallback((e) => {
    draggingRef.current = true
    e.preventDefault()

    function handleMove(moveEvent) {
      if (!draggingRef.current) return
      const nextWidth = window.innerWidth - moveEvent.clientX
      setWidth(Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, nextWidth)))
    }
    function handleUp() {
      draggingRef.current = false
      document.removeEventListener('pointermove', handleMove)
      document.removeEventListener('pointerup', handleUp)
    }
    document.addEventListener('pointermove', handleMove)
    document.addEventListener('pointerup', handleUp)
  }, [])

  async function handleSend() {
    if (pendingSelection) {
      await onExplainPending(userQuestion)
    } else {
      if (!userQuestion.trim()) return
      await onAskFreeform(userQuestion)
    }
    setUserQuestion('')
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !loading) handleSend()
  }

  return (
    <div className="chatbox-panel" style={{ width }}>
      <div className="chatbox-resizer" onPointerDown={handleResizeStart} />
      <div className="chatbox-history">
        {history.length === 0 && <p className="chatbox-empty">Chưa có giải thích nào.</p>}
        {history.map((entry) => (
          <div key={entry.id} className="chatbox-entry">
            <p className="chatbox-entry-label">{entry.label}</p>
            <div className="chatbox-entry-explanation">
              <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                {entry.explanation}
              </ReactMarkdown>
            </div>
            {entry.relatedPages.length > 0 && (
              <div className="chatbox-related-pages">
                {entry.relatedPages.map((rp, i) => (
                  <button
                    key={i}
                    type="button"
                    className="related-page-chip"
                    title={rp.reason}
                    onClick={() => onRelatedPageClick(rp.page_number, rp.highlight_term)}
                  >
                    Trang {rp.page_number}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="chatbox-pending">
        {pendingSelection && (
          <div className="chatbox-pending-preview">
            <span>
              Đã chọn (trang {pendingSelection.pageNumber}): "{truncate(pendingSelection.selectedText)}"
            </span>
            <button type="button" className="chatbox-pending-clear" onClick={onClearPending} aria-label="Bỏ chọn">
              ✕
            </button>
          </div>
        )}
        <input
          type="text"
          placeholder={pendingSelection ? 'Câu hỏi thêm (tuỳ chọn)...' : 'Hỏi về trang đang xem...'}
          value={userQuestion}
          onChange={(e) => setUserQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={loading || (!pendingSelection && !userQuestion.trim())}
        >
          {loading ? 'Đang giải thích...' : 'Explain'}
        </button>
      </div>
    </div>
  )
}
