import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Tree from 'react-d3-tree'
import {
  ChevronsDownUp,
  ChevronsUpDown,
  Focus,
  LoaderCircle,
  Minus,
  Plus,
  RotateCcw,
  Sparkles,
  X,
} from 'lucide-react'
import ChatboxPanel from './ChatboxPanel'
import { getSummary, explain } from '../api'
import { scrollToPage, scrollToPageAndHighlight } from '../scrollToPage'
import {
  buildFullTree,
  calculateFitViewport,
  clamp,
  DEPTH_GAP,
  getExpandableNodeIds,
  MAX_ZOOM,
  MIN_ZOOM,
  NODE_HEIGHT,
  NODE_WIDTH,
  ROW_GAP,
  toDisplayTree,
} from '../mindmapUtils'

function MindmapNode({ nodeDatum, selectedId, onSelect, onToggle }) {
  const isCollapsed = nodeDatum.hasChildren && nodeDatum.children.length === 0

  return (
    <g className="mindmap-node">
      <foreignObject
        width={NODE_WIDTH + 28}
        height={NODE_HEIGHT}
        x={-NODE_WIDTH / 2}
        y={-NODE_HEIGHT / 2}
      >
        <div className="mindmap-node-shell">
          <button
            type="button"
            className={`mindmap-node-button ${nodeDatum.hasChildren ? 'parent' : 'leaf'} ${
              selectedId === nodeDatum.id ? 'selected' : ''
            }`}
            aria-label={`Chọn chủ đề ${nodeDatum.name}`}
            aria-pressed={selectedId === nodeDatum.id}
            title={nodeDatum.name}
            onClick={(event) => {
              event.stopPropagation()
              onSelect(nodeDatum)
            }}
          >
            <span>{nodeDatum.name}</span>
          </button>
          {nodeDatum.hasChildren && (
            <button
              type="button"
              className={`mindmap-node-toggle ${isCollapsed ? 'collapsed' : ''}`}
              aria-label={`${isCollapsed ? 'Mở' : 'Thu'} nhánh ${nodeDatum.name}`}
              title={isCollapsed ? 'Mở nhánh' : 'Thu nhánh'}
              onClick={(event) => {
                event.stopPropagation()
                onToggle(nodeDatum.id)
              }}
            >
              <span aria-hidden="true">›</span>
            </button>
          )}
        </div>
      </foreignObject>
    </g>
  )
}

function ToolButton({ label, onClick, disabled = false, children }) {
  return (
    <button type="button" className="mindmap-tool-button" aria-label={label} title={label} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  )
}

export default function MindmapPopup({ documentId, sessionId, chatHistory, setChatHistory, onClose }) {
  const [rawTree, setRawTree] = useState(null)
  const [summaryStatus, setSummaryStatus] = useState('loading')
  const [summaryError, setSummaryError] = useState('')
  const [collapsedNodeIds, setCollapsedNodeIds] = useState(new Set())
  const [selectedNode, setSelectedNode] = useState(null)
  const [explainLoadingId, setExplainLoadingId] = useState(null)
  const [explainError, setExplainError] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const [mobileTab, setMobileTab] = useState('map')
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })
  const [viewport, setViewport] = useState({ zoom: 1, translate: { x: 0, y: 0 } })
  const [zoomLabel, setZoomLabel] = useState(1)
  const areaRef = useRef(null)
  const closeButtonRef = useRef(null)
  const requestIdRef = useRef(0)
  const mobileInitialLayoutRef = useRef(false)

  const loadSummary = useCallback(async () => {
    const requestId = ++requestIdRef.current
    setSummaryStatus('loading')
    setSummaryError('')
    try {
      const response = await getSummary(documentId)
      if (requestId !== requestIdRef.current) return
      const tree = Array.isArray(response.tree) ? response.tree : []
      setRawTree(tree)
      setSummaryStatus(tree.length > 0 ? 'ready' : 'empty')
    } catch (error) {
      if (requestId !== requestIdRef.current) return
      setRawTree(null)
      setSummaryStatus('error')
      setSummaryError(error.message || 'Không thể tải mind map.')
    }
  }, [documentId])

  useEffect(() => {
    loadSummary()
    return () => {
      requestIdRef.current += 1
    }
  }, [loadSummary])

  useEffect(() => {
    closeButtonRef.current?.focus()
    function handleKeyDown(event) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  useEffect(() => {
    const area = areaRef.current
    if (!area) return undefined

    function updateDimensions() {
      const rect = area.getBoundingClientRect()
      setDimensions({ width: rect.width, height: rect.height })
    }

    updateDimensions()
    const observer = new ResizeObserver(updateDimensions)
    observer.observe(area)
    return () => observer.disconnect()
  }, [])

  async function handleRefresh() {
    setRefreshing(true)
    setSummaryError('')
    try {
      const res = await getSummary(documentId, true)
      const tree = Array.isArray(res.tree) ? res.tree : []
      setRawTree(tree)
      setCollapsedNodeIds(new Set())
      setSummaryStatus(tree.length > 0 ? 'ready' : 'empty')
    } catch (err) {
      setSummaryError(err.message || 'Không thể tạo lại tóm tắt.')
    } finally {
      setRefreshing(false)
    }
  }

  const fullTree = useMemo(() => buildFullTree(rawTree), [rawTree])
  const displayTree = useMemo(
    () => (fullTree ? toDisplayTree(fullTree, collapsedNodeIds) : null),
    [fullTree, collapsedNodeIds],
  )
  const nodeHistory = useMemo(() => chatHistory.filter((entry) => entry.kind === 'node'), [chatHistory])

  const fitTree = useCallback(
    (collapsedIds = collapsedNodeIds) => {
      const nextViewport = calculateFitViewport(fullTree, collapsedIds, dimensions)
      setViewport(nextViewport)
      setZoomLabel(nextViewport.zoom)
    },
    [collapsedNodeIds, dimensions, fullTree],
  )

  useEffect(() => {
    if (!fullTree || dimensions.width <= 0 || dimensions.height <= 0) return
    if (dimensions.width < 500 && !mobileInitialLayoutRef.current) {
      const initiallyCollapsed = getExpandableNodeIds(fullTree)
      initiallyCollapsed.delete(fullTree.id)
      mobileInitialLayoutRef.current = true
      setCollapsedNodeIds(initiallyCollapsed)
      fitTree(initiallyCollapsed)
      return
    }
    fitTree()
  }, [dimensions.height, dimensions.width, fitTree, fullTree])

  function toggleCollapse(nodeId) {
    setCollapsedNodeIds((previous) => {
      const next = new Set(previous)
      if (next.has(nodeId)) next.delete(nodeId)
      else next.add(nodeId)
      return next
    })
  }

  function collapseAll() {
    const next = getExpandableNodeIds(fullTree)
    setCollapsedNodeIds(next)
    fitTree(next)
  }

  function expandAll() {
    const next = new Set()
    setCollapsedNodeIds(next)
    fitTree(next)
  }

  function selectNode(node) {
    setSelectedNode(node)
    setExplainError('')
    setMobileTab('details')
  }

  async function handleExplainNode() {
    if (!selectedNode || selectedNode.synthetic || explainLoadingId) return
    const target = selectedNode
    setExplainLoadingId(target.id)
    setExplainError('')
    try {
      const response = await explain({
        documentId,
        sessionId,
        mode: 'node',
        nodeId: target.id,
      })
      setChatHistory((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          kind: 'node',
          nodeId: target.id,
          label: target.name,
          explanation: response.explanation,
          relatedPages: response.related_pages || [],
        },
      ])
    } catch (error) {
      setExplainError(error.message || 'Không thể tạo giải thích.')
    } finally {
      setExplainLoadingId(null)
    }
  }

  function handlePageClick(pageNumber) {
    onClose()
    requestAnimationFrame(() => scrollToPage(pageNumber))
  }

  function updateZoom(delta) {
    const nextZoom = clamp(zoomLabel + delta, MIN_ZOOM, MAX_ZOOM)
    setViewport((previous) => ({ ...previous, zoom: nextZoom }))
    setZoomLabel(nextZoom)
  }

  return (
    <div
      className="popup-overlay mindmap-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div
        className="popup-card mindmap-popup"
        role="dialog"
        aria-modal="true"
        aria-labelledby="mindmap-title"
      >
        <header className="mindmap-header">
          <div>
            <h2 id="mindmap-title">Tóm tắt Mind Map</h2>
            <p>Chọn chủ đề để xem nhanh hoặc yêu cầu giải thích sâu.</p>
          </div>
          <div className="mindmap-toolbar" aria-label="Điều khiển mind map">
            <ToolButton label="Tạo lại tóm tắt" onClick={handleRefresh} disabled={refreshing}>
              <RotateCcw size={17} className={refreshing ? 'spin' : ''} />
            </ToolButton>
            <ToolButton label="Thu nhỏ" onClick={() => updateZoom(-0.15)} disabled={!displayTree || zoomLabel <= MIN_ZOOM}>
              <Minus size={17} />
            </ToolButton>
            <span className="mindmap-zoom-value" aria-live="polite">{Math.round(zoomLabel * 100)}%</span>
            <ToolButton label="Phóng to" onClick={() => updateZoom(0.15)} disabled={!displayTree || zoomLabel >= MAX_ZOOM}>
              <Plus size={17} />
            </ToolButton>
            <ToolButton label="Vừa màn hình" onClick={() => fitTree()} disabled={!displayTree}>
              <Focus size={17} />
            </ToolButton>
            <ToolButton label="Mở tất cả nhánh" onClick={expandAll} disabled={!displayTree}>
              <ChevronsUpDown size={17} />
            </ToolButton>
            <ToolButton label="Thu tất cả nhánh" onClick={collapseAll} disabled={!displayTree}>
              <ChevronsDownUp size={17} />
            </ToolButton>
            <ToolButton label="Đóng mind map" onClick={onClose}>
              <X size={19} />
            </ToolButton>
          </div>
        </header>

        <div className="mindmap-mobile-tabs" role="tablist" aria-label="Nội dung mind map">
          <button
            type="button"
            role="tab"
            aria-selected={mobileTab === 'map'}
            className={mobileTab === 'map' ? 'active' : ''}
            onClick={() => setMobileTab('map')}
          >
            Sơ đồ
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mobileTab === 'details'}
            className={mobileTab === 'details' ? 'active' : ''}
            onClick={() => setMobileTab('details')}
          >
            Chi tiết
          </button>
        </div>

        <div className={`popup-body mindmap-body mobile-${mobileTab}`}>
          <section className="mindmap-area" ref={areaRef} aria-label="Sơ đồ tóm tắt">
            {summaryStatus === 'loading' && (
              <div className="mindmap-state mindmap-skeleton" role="status">
                <LoaderCircle className="spin" size={22} />
                <span>Đang tạo sơ đồ...</span>
                <div />
                <div />
                <div />
              </div>
            )}
            {summaryStatus === 'error' && (
              <div className="mindmap-state" role="alert">
                <p>Không thể tải mind map.</p>
                <span>{summaryError}</span>
                <button type="button" onClick={loadSummary}>
                  <RotateCcw size={16} /> Thử lại
                </button>
              </div>
            )}
            {summaryStatus === 'empty' && (
              <div className="mindmap-state">
                <p>Tài liệu chưa có nội dung tóm tắt.</p>
              </div>
            )}
            {summaryStatus === 'ready' && displayTree && dimensions.width > 0 && (
              <Tree
                data={displayTree}
                orientation="horizontal"
                renderCustomNodeElement={(props) => (
                  <MindmapNode
                    {...props}
                    selectedId={selectedNode?.id}
                    onSelect={selectNode}
                    onToggle={toggleCollapse}
                  />
                )}
                collapsible={false}
                translate={viewport.translate}
                zoom={viewport.zoom}
                scaleExtent={{ min: MIN_ZOOM, max: MAX_ZOOM }}
                dimensions={dimensions}
                nodeSize={{ x: DEPTH_GAP, y: ROW_GAP }}
                separation={{ siblings: 1, nonSiblings: 1.15 }}
                pathFunc="step"
              />
            )}
          </section>

          <aside className="mindmap-side-panel" aria-label="Chi tiết chủ đề">
            <section className="mindmap-inspector" aria-live="polite">
              {selectedNode ? (
                <>
                  <p className="mindmap-inspector-eyebrow">Chủ đề đang chọn</p>
                  <h3>{selectedNode.name}</h3>
                  <p className="mindmap-one-liner">
                    {selectedNode.oneLiner || 'Chưa có mô tả ngắn cho chủ đề này.'}
                  </p>
                  {selectedNode.pageRefs.length > 0 && (
                    <div className="mindmap-source-pages" aria-label="Trang nguồn">
                      {selectedNode.pageRefs.map((pageNumber) => (
                        <button type="button" key={pageNumber} onClick={() => handlePageClick(pageNumber)}>
                          Trang {pageNumber}
                        </button>
                      ))}
                    </div>
                  )}
                  {!selectedNode.synthetic && (
                    <button
                      type="button"
                      className="mindmap-explain-button"
                      onClick={handleExplainNode}
                      disabled={Boolean(explainLoadingId)}
                    >
                      {explainLoadingId === selectedNode.id ? (
                        <><LoaderCircle className="spin" size={17} /> Đang giải thích...</>
                      ) : (
                        <><Sparkles size={17} /> Giải thích sâu</>
                      )}
                    </button>
                  )}
                  {explainError && <p className="mindmap-explain-error" role="alert">{explainError}</p>}
                </>
              ) : (
                <div className="mindmap-inspector-empty">
                  <p>Chọn một chủ đề trên sơ đồ.</p>
                  <span>Mô tả ngắn và trang nguồn sẽ xuất hiện tại đây.</span>
                </div>
              )}
            </section>
            <div className="mindmap-history-heading">Lịch sử giải thích</div>
            <ChatboxPanel
              history={nodeHistory}
              pendingSelection={null}
              loading={false}
              onExplainPending={async () => {}}
              onRelatedPageClick={(pageNumber, term) => {
                onClose()
                scrollToPageAndHighlight(pageNumber, term)
              }}
            />
          </aside>
        </div>
      </div>
    </div>
  )
}
