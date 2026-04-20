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
  body_md: string
  visibility: Visibility
  image_url: string | null
  created_at: string
  updated_at: string | null
  tags: TagPublic[]
}

export interface BreadcrumbPublic {
  id: number
  body_md: string
  created_at: string
  updated_at: string | null
  parent_id: number | null
}

export interface TagWithCount extends TagPublic {
  theme_count: number
}

/** Search params for the index route. Shared across components that link to "/". */
export interface StreamSearch {
  tag?: string
  q?: string
}

/** Input for POST /themes */
export interface ThemeCreateInput {
  body_md: string
  visibility?: Visibility
  tags?: { name: string }[]
}

/** Input for PUT /themes/{id} — all fields optional (partial update) */
export interface ThemeUpdateInput {
  body_md?: string
  visibility?: Visibility
  image_url?: string | null
  tags?: { name: string }[]
}

/** Response from POST /themes/{id}/generate-image */
export interface GenerateImageResponse {
  prompt: string
  candidates: string[]
}

/** Input for POST breadcrumbs */
export interface BreadcrumbInput {
  body_md: string
  parent_id?: number
}

export type DigestType = "weekly" | "monthly"

/** Digest (weekly or monthly) */
export interface DigestPublic {
  id: number
  title: string
  summary_md: string
  digest_type: DigestType
  period_start: string
  period_end: string
  status: "draft" | "published" | "sent"
  sent_at: string | null
  created_at: string
}
