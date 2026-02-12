import type { BreadcrumbPublic } from "./types"

export interface BreadcrumbNode extends BreadcrumbPublic {
  children: BreadcrumbNode[]
}

/**
 * Convert a flat list of breadcrumbs (with parent_id) into a tree.
 * Preserves chronological order from the API.
 * Orphans (parent_id points to missing breadcrumb) are treated as roots.
 */
export function buildTree(breadcrumbs: BreadcrumbPublic[]): BreadcrumbNode[] {
  const nodeMap = new Map<number, BreadcrumbNode>()
  const roots: BreadcrumbNode[] = []

  // First pass: create nodes
  for (const bc of breadcrumbs) {
    nodeMap.set(bc.id, { ...bc, children: [] })
  }

  // Second pass: link children to parents
  for (const bc of breadcrumbs) {
    const node = nodeMap.get(bc.id)!
    if (bc.parent_id != null) {
      const parent = nodeMap.get(bc.parent_id)
      if (parent) {
        parent.children.push(node)
      } else {
        roots.push(node) // orphan — treat as root
      }
    } else {
      roots.push(node)
    }
  }

  return roots
}
