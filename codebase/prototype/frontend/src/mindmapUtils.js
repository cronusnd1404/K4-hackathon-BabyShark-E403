export const NODE_WIDTH = 210
export const NODE_HEIGHT = 64
export const ROW_GAP = 88
export const DEPTH_GAP = 260
export const MIN_ZOOM = 0.35
export const MAX_ZOOM = 1.5

const VIEWPORT_PADDING = 48
const MIN_MOBILE_FIT_ZOOM = 0.55

export function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

export function convertNode(node) {
  return {
    id: node.id,
    title: node.title,
    oneLiner: node.one_liner || '',
    pageRefs: Array.isArray(node.page_refs) ? node.page_refs : [],
    synthetic: false,
    children: (node.children || []).map(convertNode),
  }
}

export function buildFullTree(treeArray) {
  const converted = (treeArray || []).map(convertNode)
  if (converted.length === 0) return null
  if (converted.length === 1) return converted[0]
  return {
    id: '__root__',
    title: 'Tổng quan',
    oneLiner: 'Các chủ đề chính trong tài liệu.',
    pageRefs: [],
    synthetic: true,
    children: converted,
  }
}

export function toDisplayTree(node, collapsedIds) {
  const hasChildren = node.children.length > 0
  return {
    name: node.title,
    id: node.id,
    oneLiner: node.oneLiner,
    pageRefs: node.pageRefs,
    synthetic: node.synthetic,
    hasChildren,
    children: collapsedIds.has(node.id)
      ? []
      : node.children.map((child) => toDisplayTree(child, collapsedIds)),
  }
}

export function getExpandableNodeIds(node, result = new Set()) {
  if (!node) return result
  if (node.children.length > 0) result.add(node.id)
  node.children.forEach((child) => getExpandableNodeIds(child, result))
  return result
}

export function calculateFitViewport(tree, collapsedIds, dimensions) {
  if (!tree || dimensions.width <= 0 || dimensions.height <= 0) {
    return { zoom: 1, translate: { x: 0, y: 0 } }
  }

  let maxDepth = 0
  let visibleLeaves = 0

  function walk(node, depth) {
    maxDepth = Math.max(maxDepth, depth)
    const visibleChildren = collapsedIds.has(node.id) ? [] : node.children
    if (visibleChildren.length === 0) {
      visibleLeaves += 1
      return
    }
    visibleChildren.forEach((child) => walk(child, depth + 1))
  }

  walk(tree, 0)
  const treeWidth = NODE_WIDTH + maxDepth * DEPTH_GAP
  const treeHeight = Math.max(NODE_HEIGHT, visibleLeaves * ROW_GAP)
  const availableWidth = Math.max(1, dimensions.width - VIEWPORT_PADDING * 2)
  const availableHeight = Math.max(1, dimensions.height - VIEWPORT_PADDING * 2)
  const minimumFitZoom = dimensions.width < 500 ? MIN_MOBILE_FIT_ZOOM : MIN_ZOOM
  const zoom = clamp(
    Math.min(availableWidth / treeWidth, availableHeight / treeHeight, 1),
    minimumFitZoom,
    MAX_ZOOM,
  )

  return {
    zoom,
    translate: {
      x: VIEWPORT_PADDING + (NODE_WIDTH * zoom) / 2,
      y: dimensions.height / 2,
    },
  }
}
