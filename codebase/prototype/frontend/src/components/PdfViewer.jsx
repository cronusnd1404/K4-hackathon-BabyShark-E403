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
  const containerRef = useRef(null)
  const ratiosRef = useRef({})

  function handleMouseUp() {
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

  return (
    <div className="pdf-viewer" ref={containerRef} onMouseUp={handleMouseUp}>
      <Document file={fileUrl} onLoadSuccess={({ numPages }) => setNumPages(numPages)}>
        {Array.from({ length: numPages }, (_, i) => i + 1).map((pageNumber) => (
          <div key={pageNumber} data-page-number={pageNumber} className="pdf-page-wrapper">
            <Page pageNumber={pageNumber} width={760} />
          </div>
        ))}
      </Document>
    </div>
  )
}
