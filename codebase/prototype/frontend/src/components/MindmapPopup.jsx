import { useEffect, useMemo, useState } from 'react'
import Tree from 'react-d3-tree'
import ChatboxPanel from './ChatboxPanel'
import { getSummary, explain } from '../api'
import { scrollToPage } from '../scrollToPage'

function convertNode(node) {
  return {
    id: node.id,
    title: node.title,
    children: (node.children || []).map(convertNode),
  }
}

function buildFullTree(treeArray) {
  const converted = treeArray.map(convertNode)
  if (converted.length === 1) return converted[0]
  return { id: '__root__', title: 'Summary', children: converted }
}

function toDisplayTree(node, collapsedIds) {
  const hasChildren = (node.children || []).length > 0
  const isCollapsed = collapsedIds.has(node.id)
  return {
    name: node.title,
    attributes: { id: node.id, hasChildren },
    children: isCollapsed ? [] : node.children.map((child) => toDisplayTree(child, collapsedIds)),
  }
}

const NODE_WIDTH = 180
const NODE_HEIGHT = 40

function MindmapNode({ nodeDatum, onExplainNode, onToggle }) {
  const { id, hasChildren } = nodeDatum.attributes
  const isCollapsed = hasChildren && (!nodeDatum.children || nodeDatum.children.length === 0)
  return (
    <g>
      <rect
        width={NODE_WIDTH}
        height={NODE_HEIGHT}
        x={-NODE_WIDTH / 2}
        y={-NODE_HEIGHT / 2}
        rx={8}
        className={`mindmap-node-box ${hasChildren ? 'parent' : 'leaf'}`}
        onClick={(e) => {
          e.stopPropagation()
          onExplainNode(id, nodeDatum.name)
        }}
      />
      <text textAnchor="middle" dy={4} style={{ pointerEvents: 'none' }}>
        {nodeDatum.name.length > 24 ? `${nodeDatum.name.slice(0, 24)}...` : nodeDatum.name}
      </text>
      {hasChildren && (
        <>
          <circle
            cx={NODE_WIDTH / 2}
            cy={0}
            r={9}
            className="mindmap-toggle-icon"
            onClick={(e) => {
              e.stopPropagation()
              onToggle(id)
            }}
          />
          <text
            x={NODE_WIDTH / 2}
            y={0}
            dy={3}
            textAnchor="middle"
            className="mindmap-toggle-label"
          >
            {isCollapsed ? '▶' : '▼'}
          </text>
        </>
      )}
    </g>
  )
}

export default function MindmapPopup({ documentId, sessionId, chatHistory, setChatHistory, onClose }) {
  const [rawTree, setRawTree] = useState(null)
  const [collapsedNodeIds, setCollapsedNodeIds] = useState(new Set())
  const [explainLoading, setExplainLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    getSummary(documentId)
      .then((res) => setRawTree(res.tree))
      .catch((err) => setError(err.message))
  }, [documentId])

  const fullTree = useMemo(() => (rawTree ? buildFullTree(rawTree) : null), [rawTree])
  const displayTree = useMemo(
    () => (fullTree ? toDisplayTree(fullTree, collapsedNodeIds) : null),
    [fullTree, collapsedNodeIds],
  )

  function toggleCollapse(nodeId) {
    setCollapsedNodeIds((prev) => {
      const next = new Set(prev)
      if (next.has(nodeId)) next.delete(nodeId)
      else next.add(nodeId)
      return next
    })
  }

  async function handleExplainNode(nodeId, nodeTitle) {
    setExplainLoading(true)
    try {
      const res = await explain({ documentId, sessionId, mode: 'node', nodeId })
      setChatHistory((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          kind: 'node',
          label: nodeTitle,
          explanation: res.explanation,
          relatedPages: res.related_pages || [],
        },
      ])
    } finally {
      setExplainLoading(false)
    }
  }

  return (
    <div className="popup-overlay">
      <div className="popup-card">
        <button type="button" className="popup-close" onClick={onClose}>
          ×
        </button>
        <h2 className="popup-title">Tóm tắt / Mindmap</h2>
        <div className="popup-body">
          <div className="mindmap-area">
            {error && <p className="error-banner">{error}</p>}
            {explainLoading && <p className="mindmap-loading">Đang giải thích...</p>}
            {displayTree && (
              <Tree
                data={displayTree}
                orientation="horizontal"
                renderCustomNodeElement={(props) => (
                  <MindmapNode {...props} onExplainNode={handleExplainNode} onToggle={toggleCollapse} />
                )}
                collapsible={false}
                translate={{ x: 150, y: 700 }}
                nodeSize={{ x: 220, y: 80 }}
                separation={{ siblings: 1, nonSiblings: 1.2 }}
              />
            )}
          </div>
          <ChatboxPanel
            history={chatHistory}
            pendingSelection={null}
            loading={false}
            onExplainPending={async () => {}}
            onRelatedPageClick={scrollToPage}
          />
        </div>
      </div>
    </div>
  )
}
