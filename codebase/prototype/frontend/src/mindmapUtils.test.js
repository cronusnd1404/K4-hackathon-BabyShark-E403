import { describe, expect, it } from 'vitest'
import {
  buildFullTree,
  calculateFitViewport,
  convertNode,
  getExpandableNodeIds,
  MAX_ZOOM,
  MIN_ZOOM,
  toDisplayTree,
} from './mindmapUtils'

const rawTree = [
  {
    id: 'n0',
    title: 'Root',
    one_liner: 'Root summary',
    page_refs: [1, 2],
    children: [
      {
        id: 'n0-0',
        title: 'Child',
        one_liner: 'Child summary',
        page_refs: [3],
        children: [],
      },
    ],
  },
]

describe('mindmap tree helpers', () => {
  it('preserves summary metadata while converting nodes', () => {
    expect(convertNode(rawTree[0])).toMatchObject({
      id: 'n0',
      title: 'Root',
      oneLiner: 'Root summary',
      pageRefs: [1, 2],
      synthetic: false,
    })
  })

  it('creates a synthetic root only for multiple top-level nodes', () => {
    expect(buildFullTree(rawTree).id).toBe('n0')
    expect(buildFullTree([...rawTree, { ...rawTree[0], id: 'n1' }])).toMatchObject({
      id: '__root__',
      synthetic: true,
    })
    expect(buildFullTree([])).toBeNull()
  })

  it('hides collapsed descendants and collects expandable nodes', () => {
    const tree = buildFullTree(rawTree)
    expect(toDisplayTree(tree, new Set(['n0'])).children).toEqual([])
    expect([...getExpandableNodeIds(tree)]).toEqual(['n0'])
  })

  it('fits the visible tree and clamps extreme zoom values', () => {
    const tree = buildFullTree(rawTree)
    const compact = calculateFitViewport(tree, new Set(), { width: 120, height: 100 })
    const spacious = calculateFitViewport(tree, new Set(['n0']), { width: 3000, height: 2000 })

    expect(compact.zoom).toBeGreaterThan(MIN_ZOOM)
    expect(spacious.zoom).toBeLessThanOrEqual(MAX_ZOOM)
    expect(spacious.translate.y).toBe(1000)
  })
})
