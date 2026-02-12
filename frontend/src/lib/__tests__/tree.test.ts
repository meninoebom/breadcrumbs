import { describe, it, expect } from "vitest"
import { buildTree } from "../tree"
import type { BreadcrumbPublic } from "../types"

function bc(id: number, parentId: number | null = null): BreadcrumbPublic {
  return {
    id,
    body_md: `breadcrumb ${id}`,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
    parent_id: parentId,
  }
}

describe("buildTree", () => {
  it("returns empty array for empty input", () => {
    expect(buildTree([])).toEqual([])
  })

  it("returns all items as roots when no parent_id set", () => {
    const result = buildTree([bc(1), bc(2), bc(3)])
    expect(result).toHaveLength(3)
    expect(result.every((n) => n.children.length === 0)).toBe(true)
  })

  it("nests child under parent", () => {
    const result = buildTree([bc(1), bc(2, 1)])
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe(1)
    expect(result[0].children).toHaveLength(1)
    expect(result[0].children[0].id).toBe(2)
  })

  it("handles multi-level nesting", () => {
    const result = buildTree([bc(1), bc(2, 1), bc(3, 2)])
    expect(result).toHaveLength(1)
    expect(result[0].children[0].children[0].id).toBe(3)
  })

  it("handles multiple roots with children", () => {
    const result = buildTree([bc(1), bc(2), bc(3, 1), bc(4, 2)])
    expect(result).toHaveLength(2)
    expect(result[0].children).toHaveLength(1)
    expect(result[1].children).toHaveLength(1)
  })

  it("treats orphans as roots", () => {
    const result = buildTree([bc(1), bc(2, 999)])
    expect(result).toHaveLength(2)
  })
})
