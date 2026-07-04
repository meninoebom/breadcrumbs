import { useCallback, useEffect, useRef, useState } from "react"

const DEBOUNCE_MS = 300

function readDraft(key: string, enabled: boolean): string {
  if (!enabled) return ""
  try {
    return localStorage.getItem(key) ?? ""
  } catch {
    // localStorage unavailable (private mode / disabled) — drafts are best-effort.
    return ""
  }
}

/**
 * A string value mirrored to localStorage so in-progress writing survives a
 * stray navigation, dialog dismiss, or tab discard.
 *
 * Restores on mount (so remount the consumer via a `key` prop when the storage
 * key changes), persists on change behind a short debounce, and clears the
 * stored value when emptied or when `clear()` is called after a successful save.
 * Pass `enabled: false` to make it behave like plain `useState` (e.g. for reply
 * forms that shouldn't own a draft).
 */
export function useDraft(
  key: string,
  { enabled = true }: { enabled?: boolean } = {},
): [string, (value: string) => void, () => void] {
  const [value, setValue] = useState(() => readDraft(key, enabled))
  const timer = useRef<ReturnType<typeof setTimeout>>(null)

  useEffect(() => {
    if (!enabled) return
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => {
      try {
        if (value) localStorage.setItem(key, value)
        else localStorage.removeItem(key)
      } catch {
        // best-effort persistence; ignore quota/availability errors
      }
    }, DEBOUNCE_MS)
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [key, value, enabled])

  const clear = useCallback(() => {
    setValue("")
    if (!enabled) return
    try {
      localStorage.removeItem(key)
    } catch {
      // best-effort
    }
  }, [key, enabled])

  return [value, setValue, clear]
}
