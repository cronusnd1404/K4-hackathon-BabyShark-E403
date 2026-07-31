import { useEffect, useState, useCallback } from 'react'
import PdfViewer from './PdfViewer'
import ChatboxPanel from './ChatboxPanel'
import MindmapPopup from './MindmapPopup'
import ExercisePopup from './ExercisePopup'
import { getIngestStatus, ingestPdf, listDocuments, pdfUrl, explain } from '../api'
import { scrollToPage } from '../scrollToPage'

const SAMPLE_PDF_FILENAME = 'L11-SVM.pdf'

export default function MainScreen({ sessionId, documentId, setDocumentId, chatHistory, setChatHistory }) {
  const [documents, setDocuments] = useState([])
  const [selectedFilename, setSelectedFilename] = useState(SAMPLE_PDF_FILENAME)
  const [ingestion, setIngestion] = useState(null)
  const [ingestError, setIngestError] = useState(null)
  const [pendingSelection, setPendingSelection] = useState(null)
  const [explainLoading, setExplainLoading] = useState(false)
  const [currentPageNumber, setCurrentPageNumber] = useState(1)
  const [activePopup, setActivePopup] = useState(null) // null | 'mindmap' | 'exercise'

  const loadDocument = useCallback(async (pdfFilename) => {
    setIngestError(null)
    setIngestion({ status: 'queued', processed_pages: 0, total_pages: 0 })
    setDocumentId(null)
    setPendingSelection(null)
    setCurrentPageNumber(1)
    setActivePopup(null)
    setChatHistory([])
    try {
      const result = await ingestPdf(pdfFilename)
      setDocumentId(result.document_id)
      setIngestion(result)
    } catch (err) {
      setIngestError(err.message)
      setIngestion(null)
    }
  }, [setChatHistory, setDocumentId])

  useEffect(() => {
    let cancelled = false
    listDocuments()
      .then((rows) => {
        if (cancelled) return
        setDocuments(rows)
        const initial = rows.find((doc) => doc.pdf_filename === SAMPLE_PDF_FILENAME) || rows[0]
        if (initial) {
          setSelectedFilename(initial.pdf_filename)
          return loadDocument(initial.pdf_filename)
        }
        throw new Error('Không tìm thấy PDF nào trong backend/data/raw_pdfs')
      })
      .catch((err) => setIngestError(err.message))
    return () => {
      cancelled = true
    }
  }, [loadDocument])

  useEffect(() => {
    if (!ingestion?.job_id || !['queued', 'processing'].includes(ingestion.status)) return
    let cancelled = false
    const timer = setTimeout(async () => {
      try {
        const next = await getIngestStatus(ingestion.job_id)
        if (!cancelled) {
          setIngestion(next)
          if (next.status === 'failed') setIngestError(next.error || 'Không thể đọc nội dung PDF')
        }
      } catch (err) {
        if (!cancelled) setIngestError(err.message)
      }
    }, 1000)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [ingestion])

  function handleDocumentChange(event) {
    const filename = event.target.value
    setSelectedFilename(filename)
    loadDocument(filename)
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
    } catch (err) {
      setIngestError(err.message)
    } finally {
      setExplainLoading(false)
    }
  }

  const isReady = ['ready', 'ready_with_warnings'].includes(ingestion?.status)
  const isProcessing = ['queued', 'processing'].includes(ingestion?.status)
  const progressTotal = ingestion?.total_pages || 0
  const progressCurrent = ingestion?.processed_pages || 0

  return (
    <div className="main-screen">
      <aside className="sidebar">
        <div className="sidebar-item active">Day01</div>
        <div className="sidebar-item disabled">Day02</div>
        <div className="sidebar-item disabled">Day03</div>
      </aside>

      <main className="pdf-column">
        <div className="header-buttons">
          <label className="document-picker">
            <span>Tài liệu</span>
            <select
              value={selectedFilename}
              onChange={handleDocumentChange}
              disabled={!documents.length || isProcessing}
            >
              {documents.map((doc) => (
                <option key={doc.pdf_filename} value={doc.pdf_filename}>
                  {doc.title}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="header-button"
            onClick={() => setActivePopup('mindmap')}
            disabled={!isReady}
          >
            <span aria-hidden="true">🧠</span> Tạo tóm tắt
          </button>
          <button
            type="button"
            className="header-button"
            onClick={() => setActivePopup('exercise')}
            disabled={!isReady}
          >
            <span aria-hidden="true">📝</span> Tạo bài tập
          </button>
        </div>

        {ingestError && <p className="error-banner">Không thể tải PDF: {ingestError}</p>}
        {isProcessing && (
          <div className="ingest-progress" role="status">
            <span>Đang đọc nội dung PDF: {progressCurrent}/{progressTotal || '?'} trang</span>
            {progressTotal > 0 && (
              <progress value={progressCurrent} max={progressTotal}>
                {progressCurrent}/{progressTotal}
              </progress>
            )}
          </div>
        )}
        {ingestion?.status === 'ready_with_warnings' && (
          <p className="warning-banner">
            Đã đọc PDF nhưng có {ingestion.warnings?.length || 0} trang/cảnh báo cần kiểm tra.
          </p>
        )}
        {!documentId && !ingestError && <p className="pdf-loading">Đang mở PDF...</p>}
        {documentId && (
          <PdfViewer
            key={documentId}
            fileUrl={pdfUrl(documentId)}
            onTextSelected={isReady ? (selection) => setPendingSelection(selection) : null}
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
