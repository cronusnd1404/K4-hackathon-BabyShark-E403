import { useEffect, useState, useCallback } from 'react'
import PdfViewer from './PdfViewer'
import ChatboxPanel from './ChatboxPanel'
import MindmapPopup from './MindmapPopup'
import ExercisePopup from './ExercisePopup'
import { ingestPdf, pdfUrl, explain } from '../api'
import { scrollToPage } from '../scrollToPage'

const SAMPLE_PDF_FILENAME = 'L11-SVM.pdf'

export default function MainScreen({ sessionId, documentId, setDocumentId, chatHistory, setChatHistory }) {
  const [ingestError, setIngestError] = useState(null)
  const [pendingSelection, setPendingSelection] = useState(null)
  const [explainLoading, setExplainLoading] = useState(false)
  const [currentPageNumber, setCurrentPageNumber] = useState(1)
  const [activePopup, setActivePopup] = useState(null) // null | 'mindmap' | 'exercise'

  useEffect(() => {
    if (documentId) return
    ingestPdf(SAMPLE_PDF_FILENAME)
      .then((res) => setDocumentId(res.document_id))
      .catch((err) => setIngestError(err.message))
  }, [documentId, setDocumentId])

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

  return (
    <div className="main-screen">
      <aside className="sidebar">
        <div className="sidebar-item active">Day01</div>
        <div className="sidebar-item disabled">Day02</div>
        <div className="sidebar-item disabled">Day03</div>
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
        onRelatedPageClick={scrollToPage}
      />

      {activePopup === 'mindmap' && documentId && (
        <MindmapPopup
          documentId={documentId}
          sessionId={sessionId}
          chatHistory={chatHistory}
          setChatHistory={setChatHistory}
          onClose={() => setActivePopup(null)}
        />
      )}

      {activePopup === 'exercise' && documentId && (
        <ExercisePopup
          documentId={documentId}
          sessionId={sessionId}
          pageNumber={currentPageNumber}
          onClose={() => setActivePopup(null)}
        />
      )}
    </div>
  )
}
