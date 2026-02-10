import type { ThemePublic, BreadcrumbPublic } from "./types"

/**
 * Query key conventions (consistent across Issues #10-12):
 *   Theme lists:  ["themes", { visibility?, tag?, q? }]
 *   Breadcrumbs:  ["themes", themeId, "breadcrumbs"]
 */

export interface ThemeSearchParams {
  visibility?: string
  tag?: string
  q?: string
  limit?: number
  offset?: number
}

export async function fetchThemes(
  params?: ThemeSearchParams,
): Promise<ThemePublic[]> {
  const searchParams = new URLSearchParams()
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) searchParams.set(key, String(value))
    }
  }
  const qs = searchParams.toString()
  const url = `/api/themes${qs ? `?${qs}` : ""}`

  let res: Response
  try {
    res = await fetch(url)
  } catch {
    throw new Error(
      "Cannot reach the API. Is the backend running? (uv run dev)",
    )
  }
  if (!res.ok) throw new Error(`Failed to fetch themes (${res.status})`)
  return res.json()
}

export async function fetchBreadcrumbs(
  themeId: number,
): Promise<BreadcrumbPublic[]> {
  let res: Response
  try {
    res = await fetch(`/api/themes/${themeId}/breadcrumbs`)
  } catch {
    throw new Error(
      "Cannot reach the API. Is the backend running? (uv run dev)",
    )
  }
  if (!res.ok) throw new Error(`Failed to fetch breadcrumbs (${res.status})`)
  return res.json()
}
