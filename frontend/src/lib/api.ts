import type {
  BreadcrumbPublic,
  TagWithCount,
  ThemePublic,
  Visibility,
} from "./types"

/**
 * Query key conventions (consistent across Issues #10-12):
 *   Theme lists:  ["themes", { visibility?, tag?, q? }]
 *   Breadcrumbs:  ["themes", themeId, "breadcrumbs"]
 */

export interface ThemeSearchParams {
  visibility?: Visibility
  tag?: string
  q?: string
  limit?: number
  offset?: number
}

async function apiFetch<T>(url: string, label: string): Promise<T> {
  let res: Response
  try {
    res = await fetch(url)
  } catch (err) {
    throw new Error(
      "Cannot reach the API. Is the backend running? (uv run dev)",
      { cause: err },
    )
  }
  if (!res.ok) {
    let detail = ""
    try {
      const body = await res.json()
      detail =
        typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail)
    } catch {
      // Response body wasn't JSON — status code is still useful
    }
    throw new Error(
      `Failed to fetch ${label} (${res.status})${detail ? `: ${detail}` : ""}`,
    )
  }
  return res.json()
}

function buildQueryString(
  params?: Record<string, string | number | undefined>,
): string {
  if (!params) return ""
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) searchParams.set(key, String(value))
  }
  const qs = searchParams.toString()
  return qs ? `?${qs}` : ""
}

export function fetchThemes(
  params?: ThemeSearchParams,
): Promise<ThemePublic[]> {
  const url = `/api/themes${buildQueryString(params as Record<string, string | number | undefined>)}`
  return apiFetch(url, "themes")
}

export function fetchBreadcrumbs(
  themeId: number,
): Promise<BreadcrumbPublic[]> {
  return apiFetch(`/api/themes/${themeId}/breadcrumbs`, "breadcrumbs")
}

export function fetchTags(): Promise<TagWithCount[]> {
  return apiFetch("/api/tags", "tags")
}

