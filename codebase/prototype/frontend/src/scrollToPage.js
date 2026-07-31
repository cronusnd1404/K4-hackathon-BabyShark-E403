const HIGHLIGHT_CLASS = 'pdf-term-highlight'
const HIGHLIGHT_DURATION_MS = 2800

export function scrollToPage(pageNumber) {
  document.querySelector(`[data-page-number="${pageNumber}"]`)?.scrollIntoView({ behavior: 'smooth' })
}

// Scrolls to the page, then finds and highlights the specific term within
// react-pdf's text layer (each text-layer span has `color: transparent` --
// it exists only for text selection, the visible glyphs are drawn on the
// canvas underneath -- so adding a background-color to the matching span
// paints a highlight box over the real text without covering it).
export function scrollToPageAndHighlight(pageNumber, term) {
  const pageEl = document.querySelector(`[data-page-number="${pageNumber}"]`)
  if (!pageEl) return
  pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
  if (!term) return

  const needle = term.toLowerCase()

  function trySearch(attemptsLeft) {
    const spans = pageEl.querySelectorAll('.react-pdf__Page__textContent [role="presentation"]')
    const match = Array.from(spans).find((span) => span.textContent.toLowerCase().includes(needle))

    if (match) {
      match.classList.add(HIGHLIGHT_CLASS)
      match.scrollIntoView({ behavior: 'smooth', block: 'center' })
      setTimeout(() => match.classList.remove(HIGHLIGHT_CLASS), HIGHLIGHT_DURATION_MS)
      return
    }
    // Text layer renders async right after a page first scrolls into view --
    // give react-pdf a moment and retry before giving up silently.
    if (attemptsLeft > 0) setTimeout(() => trySearch(attemptsLeft - 1), 200)
  }

  setTimeout(() => trySearch(5), 300)
}
