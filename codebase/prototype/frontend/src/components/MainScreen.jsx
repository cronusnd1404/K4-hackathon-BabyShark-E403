import { lazy, Suspense, useEffect, useState, useCallback } from 'react'
import PdfViewer from './PdfViewer'
import ChatboxPanel from './ChatboxPanel'
import ExercisePopup from './ExercisePopup'
import { ingestPdf, listPdfs, pdfUrl, explain } from '../api'
import { scrollToPageAndHighlight } from '../scrollToPage'

const DEFAULT_PDF_FILENAME = 'L11-SVM.pdf'
const MindmapPopup = lazy(() => import('./MindmapPopup'))

export default function MainScreen({ sessionId, documentId, setDocumentId, chatHistory, setChatHistory }) {
  const [pdfList, setPdfList] = useState([])
  const [selectedFilename, setSelectedFilename] = useState(null)
  const [ingestError, setIngestError] = useState(null)
  const [pendingSelection, setPendingSelection] = useState(null)
  const [explainLoading, setExplainLoading] = useState(false)
  const [currentPageNumber, setCurrentPageNumber] = useState(1)
  const [activePopup, setActivePopup] = useState(null) // null | 'mindmap' | 'exercise'

  useEffect(() => {
    listPdfs()
      .then((list) => {
        setPdfList(list)
        setSelectedFilename(
          (prev) =>
            prev ||
            list.find((p) => p.filename === DEFAULT_PDF_FILENAME)?.filename ||
            list[0]?.filename ||
            null,
        )
      })
      .catch((err) => setIngestError(err.message))
  }, [])

  useEffect(() => {
    if (!selectedFilename) return
    setDocumentId(null)
    setIngestError(null)
    ingestPdf(selectedFilename)
      .then((res) => setDocumentId(res.document_id))
      .catch((err) => setIngestError(err.message))
  }, [selectedFilename, setDocumentId])

  function handleSelectPdf(filename) {
    if (filename === selectedFilename) return
    setSelectedFilename(filename)
    setCurrentPageNumber(1)
    setPendingSelection(null)
    setChatHistory([])
  }

  const handleCurrentPageChange = useCallback((pageNumber) => {
    setCurrentPageNumber(pageNumber)
  }, [])

  async function handleExplainPending(userQuestion) {
    if (!pendingSelection) return
    setExplainLoading(true)
    try {
      const res = await explain({
        documentId,
        sessionId,
        mode: 'highlight',
        pageNumber: pendingSelection.pageNumber,
        selectedText: pendingSelection.selectedText,
        userQuestion: userQuestion || undefined,
      })
      setChatHistory((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          kind: 'highlight',
          label: `"${pendingSelection.selectedText}" (trang ${pendingSelection.pageNumber})`,
          explanation: res.explanation,
          relatedPages: res.related_pages || [],
        },
      ])
      setPendingSelection(null)
    } finally {
      setExplainLoading(false)
    }
  }

  async function handleAskFreeform(userQuestion) {
    setExplainLoading(true)
    try {
      // Context window = 3: only the last 3 free-form chat turns (not highlight
      // explanations) are replayed back to the model as conversation history.
      const recentTurns = chatHistory
        .filter((e) => e.kind === 'question')
        .slice(-3)
        .map((e) => ({ question: e.question, answer: e.explanation }))

      const res = await explain({
        documentId,
        sessionId,
        mode: 'question',
        pageNumber: currentPageNumber,
        userQuestion,
        chatHistory: recentTurns,
      })
      setChatHistory((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          kind: 'question',
          label: `Câu hỏi (trang ${currentPageNumber}): "${userQuestion}"`,
          question: userQuestion,
          explanation: res.explanation,
          relatedPages: res.related_pages || [],
        },
      ])
    } finally {
      setExplainLoading(false)
    }
  }

  return (
    <div className="main-screen">
      <aside className="sidebar">
        {pdfList.map((pdf) => (
          <button
            key={pdf.filename}
            type="button"
            className={`sidebar-item${pdf.filename === selectedFilename ? ' active' : ''}`}
            onClick={() => handleSelectPdf(pdf.filename)}
          >
            {pdf.label}
          </button>
        ))}
      </aside>

      <main className="pdf-column">
        <div className="header-buttons">
          <button type="button" className="header-button" onClick={() => setActivePopup('mindmap')}>
            <span aria-hidden="true">🧠</span> Tạo tóm tắt
          </button>
          <button type="button" className="header-button" onClick={() => setActivePopup('exercise')}>
            <span aria-hidden="true">📝</span> Tạo bài tập
          </button>
        </div>

        {ingestError && <p className="error-banner">Failed to load PDF: {ingestError}</p>}
        {!documentId && !ingestError && <p>Loading PDF...</p>}
        {documentId && (
          <PdfViewer
            fileUrl={pdfUrl(documentId)}
            onTextSelected={(sel) => setPendingSelection(sel)}
            onCurrentPageChange={handleCurrentPageChange}
          />
        )}
      </main>

      <ChatboxPanel
        history={chatHistory}
        pendingSelection={pendingSelection}
        loading={explainLoading}
        onExplainPending={handleExplainPending}
        onAskFreeform={handleAskFreeform}
        onClearPending={() => setPendingSelection(null)}
        onRelatedPageClick={scrollToPageAndHighlight}
      />

      {activePopup === 'mindmap' && documentId && (
        <Suspense
          fallback={
            <div className="popup-overlay" role="status">
              <div className="popup-loading">Đang mở mind map...</div>
            </div>
          }
        >
          <MindmapPopup
            documentId={documentId}
            sessionId={sessionId}
            chatHistory={chatHistory}
            setChatHistory={setChatHistory}
            onClose={() => setActivePopup(null)}
          />
        </Suspense>
      )}

      {activePopup === 'exercise' && documentId && (
        <ExercisePopup documentId={documentId} sessionId={sessionId} onClose={() => setActivePopup(null)} />
      )}
    </div>
  )
}
