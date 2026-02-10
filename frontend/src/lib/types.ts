/**
 * API response types for the Breadcrumbs backend.
 *
 * These are intentional subsets of what the API returns — we only
 * declare the fields we consume on the frontend. If a new feature
 * needs additional fields, add them here.
 */

export interface TagPublic {
  id: number
  name: string
}

export type Visibility = "draft" | "published"

export interface ThemePublic {
  id: number
  title: string
  description_md: string | null
  visibility: Visibility
  created_at: string
  updated_at: string | null
  tags: TagPublic[]
}

export interface BreadcrumbPublic {
  id: number
  body_md: string
  created_at: string
  updated_at: string | null
}
