import { useEffect, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()

export default function PdfViewer({ fileUrl, onTextSelected, onCurrentPageChange }) {
  const [numPages, setNumPages] = useState(0)
  const [pageWidth, setPageWidth] = useState(760)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [retryKey, setRetryKey] = useState(0)
  const containerRef = useRef(null)
  const ratiosRef = useRef({})

  function handleMouseUp() {
    if (!onTextSelected) return
    const selection = window.getSelection()
    const text = selection ? selection.toString().trim() : ''
    if (!text) return
    const anchorNode = selection.anchorNode
    const el = anchorNode?.nodeType === 3 ? anchorNode.parentElement : anchorNode
    const pageEl = el?.closest('[data-page-number]')
    if (!pageEl) return
    const pageNumber = parseInt(pageEl.getAttribute('data-page-number'), 10)
    onTextSelected({ pageNumber, selectedText: text })
  }

  useEffect(() => {
    setNumPages(0)
    setLoading(true)
    setLoadError(null)
    ratiosRef.current = {}
  }, [fileUrl, retryKey])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const updateWidth = () => {
      const available = Math.max(280, container.clientWidth - 48)
      setPageWidth(Math.min(900, available))
    }
    updateWidth()
    const observer = new ResizeObserver(updateWidth)
    observer.observe(container)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!numPages || !onCurrentPageChange) return
    const container = containerRef.current
    if (!container) return

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const pageNumber = parseInt(entry.target.getAttribute('data-page-number'), 10)
          ratiosRef.current[pageNumber] = entry.intersectionRatio
        })
        let maxPage = null
        let maxRatio = 0
        for (const [page, ratio] of Object.entries(ratiosRef.current)) {
          if (ratio > maxRatio) {
            maxRatio = ratio
            maxPage = parseInt(page, 10)
          }
        }
        if (maxPage !== null) onCurrentPageChange(maxPage)
      },
      { root: container, threshold: [0, 0.1, 0.25, 0.5, 0.75, 1] },
    )

    const wrappers = container.querySelectorAll('.pdf-page-wrapper')
    wrappers.forEach((el) => observer.observe(el))
    return () => observer.disconnect()
  }, [numPages, onCurrentPageChange])

  function handleLoadSuccess({ numPages: loadedPages }) {
    setNumPages(loadedPages)
    setLoading(false)
    setLoadError(null)
  }

  function handleLoadError(error) {
    setLoading(false)
    const message = error?.message || 'Không thể tải PDF'
    setLoadError(
      `${message}. Kiểm tra backend cổng 8020, CORS và đường dẫn tài liệu.`,
    )
  }

  return (
    <div className="pdf-viewer" ref={containerRef} onMouseUp={handleMouseUp}>
      {loading && <p className="pdf-loading">Đang tải PDF...</p>}
      {loadError && (
        <div className="pdf-error" role="alert">
          <p>{loadError}</p>
          <button type="button" onClick={() => setRetryKey((value) => value + 1)}>
            Thử lại
          </button>
        </div>
      )}
      <Document
        key={`${fileUrl}-${retryKey}`}
        file={fileUrl}
        onLoadSuccess={handleLoadSuccess}
        onLoadError={handleLoadError}
        onSourceError={handleLoadError}
        loading={null}
        error={null}
        className="pdf-document"
      >
        {Array.from({ length: numPages }, (_, i) => i + 1).map((pageNumber) => (
          <div key={pageNumber} data-page-number={pageNumber} className="pdf-page-wrapper">
            <Page
              pageNumber={pageNumber}
              width={pageWidth}
              loading={<p className="pdf-page-loading">Đang render trang {pageNumber}...</p>}
            />
          </div>
        ))}
      </Document>
    </div>
  )
}
