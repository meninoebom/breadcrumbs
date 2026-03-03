import { clearToken, getToken } from "./auth"
import type {
  BreadcrumbInput,
  BreadcrumbPublic,
  DigestPublic,
  DigestType,
  TagWithCount,
  ThemeCreateInput,
  ThemePublic,
  ThemeUpdateInput,
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

async function apiFetch<T>(url: string, label: string, headers?: Record<string, string>): Promise<T> {
  let res: Response
  try {
    res = await fetch(url, headers ? { headers } : undefined)
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

// ---------------------------------------------------------------------------
// Mutation helper (POST / PUT / DELETE)
// ---------------------------------------------------------------------------

async function apiMutate<T = void>(
  url: string,
  { method, body, label }: { method: string; body?: unknown; label: string },
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {}
  if (body) headers["Content-Type"] = "application/json"
  if (token) headers["Authorization"] = `Bearer ${token}`

  let res: Response
  try {
    res = await fetch(url, {
      method,
      headers: Object.keys(headers).length ? headers : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch (err) {
    throw new Error(
      "Cannot reach the API. Is the backend running? (uv run dev)",
      { cause: err },
    )
  }
  if (!res.ok) {
    if (res.status === 401) {
      clearToken()
      window.location.href = "/login"
      throw new Error("Authentication required")
    }
    let detail = ""
    try {
      const b = await res.json()
      detail = typeof b.detail === "string" ? b.detail : JSON.stringify(b.detail)
    } catch {
      // Response body wasn't JSON
    }
    throw new Error(
      `Failed to ${label} (${res.status})${detail ? `: ${detail}` : ""}`,
    )
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

// ---------------------------------------------------------------------------
// Single-theme fetch
// ---------------------------------------------------------------------------

export function fetchTheme(themeId: number): Promise<ThemePublic> {
  return apiFetch(`/api/themes/${themeId}`, "theme")
}

// ---------------------------------------------------------------------------
// Theme mutations
// ---------------------------------------------------------------------------

export function createTheme(data: ThemeCreateInput): Promise<ThemePublic> {
  return apiMutate("/api/themes", {
    method: "POST",
    body: data,
    label: "create theme",
  })
}

export function updateTheme(
  themeId: number,
  data: ThemeUpdateInput,
): Promise<ThemePublic> {
  return apiMutate(`/api/themes/${themeId}`, {
    method: "PUT",
    body: data,
    label: "update theme",
  })
}

export function deleteTheme(themeId: number): Promise<void> {
  return apiMutate(`/api/themes/${themeId}`, {
    method: "DELETE",
    label: "delete theme",
  })
}

// ---------------------------------------------------------------------------
// Breadcrumb mutations
// ---------------------------------------------------------------------------

export function createBreadcrumb(
  themeId: number,
  data: BreadcrumbInput,
): Promise<BreadcrumbPublic> {
  return apiMutate(`/api/themes/${themeId}/breadcrumbs`, {
    method: "POST",
    body: data,
    label: "create breadcrumb",
  })
}

export function updateBreadcrumb(
  themeId: number,
  breadcrumbId: number,
  data: BreadcrumbInput,
): Promise<BreadcrumbPublic> {
  return apiMutate(`/api/themes/${themeId}/breadcrumbs/${breadcrumbId}`, {
    method: "PUT",
    body: data,
    label: "update breadcrumb",
  })
}

export function deleteBreadcrumb(
  themeId: number,
  breadcrumbId: number,
): Promise<void> {
  return apiMutate(`/api/themes/${themeId}/breadcrumbs/${breadcrumbId}`, {
    method: "DELETE",
    label: "delete breadcrumb",
  })
}

// ---------------------------------------------------------------------------
// Weekly digests
// ---------------------------------------------------------------------------

export function fetchDigests(params?: {
  limit?: number
  offset?: number
}): Promise<DigestPublic[]> {
  const url = `/api/digests${buildQueryString(params as Record<string, string | number | undefined>)}`
  return apiFetch(url, "digests")
}

export function fetchDigest(digestId: number): Promise<DigestPublic> {
  return apiFetch(`/api/digests/${digestId}`, "digest")
}

export function fetchAllDigests(): Promise<DigestPublic[]> {
  const token = getToken()
  return apiFetch("/api/digests/admin", "digests (admin)", token ? { Authorization: `Bearer ${token}` } : undefined)
}

export function generateDigest(digestType: DigestType = "weekly"): Promise<DigestPublic> {
  return apiMutate(`/api/digests/generate?digest_type=${digestType}`, {
    method: "POST",
    label: "generate digest",
  })
}

export function publishDigest(digestId: number): Promise<DigestPublic> {
  return apiMutate(`/api/digests/${digestId}/publish`, {
    method: "POST",
    label: "publish digest",
  })
}

export function sendDigest(digestId: number): Promise<{ sent: number; failed: number; skipped: number }> {
  return apiMutate(`/api/digests/${digestId}/send`, {
    method: "POST",
    label: "send digest",
  })
}

export function subscribe(email: string): Promise<{ message: string }> {
  return apiMutate("/api/subscribers/subscribe", {
    method: "POST",
    body: { email },
    label: "subscribe",
  })
}

