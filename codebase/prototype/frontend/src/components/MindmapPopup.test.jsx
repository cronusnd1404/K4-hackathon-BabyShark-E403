import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import MindmapPopup from './MindmapPopup'
import { explain, getSummary } from '../api'
import { scrollToPage } from '../scrollToPage'

vi.mock('../api', () => ({
  getSummary: vi.fn(),
  explain: vi.fn(),
}))

vi.mock('../scrollToPage', () => ({
  scrollToPage: vi.fn(),
}))

vi.mock('react-d3-tree', () => ({
  default: ({ data, renderCustomNodeElement }) => {
    const nodes = []
    function collect(node) {
      nodes.push(renderCustomNodeElement({ nodeDatum: node }))
      node.children.forEach(collect)
    }
    collect(data)
    return <svg data-testid="mindmap-tree">{nodes}</svg>
  },
}))

const summaryTree = [
  {
    id: 'n0',
    title: 'Support Vector Machines',
    one_liner: 'Phân loại bằng siêu phẳng có biên lớn nhất.',
    page_refs: [4, 5],
    children: [
      {
        id: 'n0-0',
        title: 'Kernel trick',
        one_liner: 'Ánh xạ dữ liệu gián tiếp.',
        page_refs: [44],
        children: [],
      },
    ],
  },
]

function renderPopup(overrides = {}) {
  const props = {
    documentId: 'doc-1',
    sessionId: 'session-1',
    chatHistory: [],
    setChatHistory: vi.fn(),
    onClose: vi.fn(),
    ...overrides,
  }
  return { ...render(<MindmapPopup {...props} />), props }
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({
    width: 900,
    height: 620,
    top: 0,
    right: 900,
    bottom: 620,
    left: 0,
    x: 0,
    y: 0,
    toJSON: () => {},
  })
  getSummary.mockResolvedValue({ tree: summaryTree })
})

describe('MindmapPopup', () => {
  it('loads the tree, previews a node, and filters history to mind map entries', async () => {
    renderPopup({
      chatHistory: [
        {
          id: 'highlight-1',
          kind: 'highlight',
          label: 'PDF highlight',
          explanation: 'Hidden here',
          relatedPages: [],
        },
        {
          id: 'node-1',
          kind: 'node',
          label: 'Previous node',
          explanation: 'Visible here',
          relatedPages: [],
        },
      ],
    })

    const nodeButton = await screen.findByRole('button', { name: 'Chọn chủ đề Support Vector Machines' })
    fireEvent.click(nodeButton)

    expect(explain).not.toHaveBeenCalled()
    expect(screen.getByText('Phân loại bằng siêu phẳng có biên lớn nhất.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Trang 4' })).toBeInTheDocument()
    expect(screen.getByText('Previous node')).toBeInTheDocument()
    expect(screen.queryByText('PDF highlight')).not.toBeInTheDocument()
  })

  it('requests a deep explanation once and appends it to global history', async () => {
    let resolveExplain
    explain.mockReturnValue(new Promise((resolve) => {
      resolveExplain = resolve
    }))
    const { props } = renderPopup()

    fireEvent.click(await screen.findByRole('button', { name: 'Chọn chủ đề Support Vector Machines' }))
    const explainButton = screen.getByRole('button', { name: 'Giải thích sâu' })
    fireEvent.click(explainButton)
    fireEvent.click(explainButton)

    expect(explain).toHaveBeenCalledTimes(1)
    expect(explain).toHaveBeenCalledWith({
      documentId: 'doc-1',
      sessionId: 'session-1',
      mode: 'node',
      nodeId: 'n0',
    })
    expect(screen.getByRole('button', { name: 'Đang giải thích...' })).toBeDisabled()

    resolveExplain({
      explanation: 'SVM explanation',
      related_pages: [{ page_number: 8, reason: 'Margin' }],
    })

    await waitFor(() => expect(props.setChatHistory).toHaveBeenCalledTimes(1))
    const updateHistory = props.setChatHistory.mock.calls[0][0]
    expect(updateHistory([])[0]).toMatchObject({
      kind: 'node',
      nodeId: 'n0',
      label: 'Support Vector Machines',
      explanation: 'SVM explanation',
    })
  })

  it('shows explanation errors without losing the selected node', async () => {
    explain.mockRejectedValue(new Error('Model unavailable'))
    renderPopup()

    fireEvent.click(await screen.findByRole('button', { name: 'Chọn chủ đề Support Vector Machines' }))
    fireEvent.click(screen.getByRole('button', { name: 'Giải thích sâu' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Model unavailable')
    expect(screen.getByText('Support Vector Machines', { selector: 'h3' })).toBeInTheDocument()
  })

  it('supports summary retry and empty states', async () => {
    getSummary.mockRejectedValueOnce(new Error('Network down')).mockResolvedValueOnce({ tree: [] })
    renderPopup()

    expect(await screen.findByText('Không thể tải mind map.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Thử lại' }))
    expect(await screen.findByText('Tài liệu chưa có nội dung tóm tắt.')).toBeInTheDocument()
    expect(getSummary).toHaveBeenCalledTimes(2)
  })

  it('closes before navigating to a source page and closes with Escape', async () => {
    const { props } = renderPopup()

    fireEvent.click(await screen.findByRole('button', { name: 'Chọn chủ đề Support Vector Machines' }))
    fireEvent.click(screen.getByRole('button', { name: 'Trang 4' }))
    expect(props.onClose).toHaveBeenCalledTimes(1)
    expect(scrollToPage).toHaveBeenCalledWith(4)

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(props.onClose).toHaveBeenCalledTimes(2)
  })

  it('exposes branch, viewport, and dialog controls with accessible labels', async () => {
    renderPopup()

    expect(screen.getByRole('dialog', { name: 'Tóm tắt Mind Map' })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Thu nhánh Support Vector Machines' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Thu tất cả nhánh' }))
    expect(screen.getByRole('button', { name: 'Mở nhánh Support Vector Machines' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Mở tất cả nhánh' }))
    expect(screen.getByRole('button', { name: 'Thu nhánh Support Vector Machines' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Vừa màn hình' })).toBeEnabled()
  })
})
