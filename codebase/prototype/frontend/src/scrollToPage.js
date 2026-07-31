export function scrollToPage(pageNumber) {
  document.querySelector(`[data-page-number="${pageNumber}"]`)?.scrollIntoView({ behavior: 'smooth' })
}
