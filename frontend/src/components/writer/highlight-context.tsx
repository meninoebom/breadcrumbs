import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react"

interface HighlightContextValue {
  /** The breadcrumb id to visually highlight, or null. */
  highlightedId: number | null
  /** Mark a breadcrumb as just-added so its card highlights briefly. */
  highlight: (id: number) => void
}

const HighlightContext = createContext<HighlightContextValue>({
  highlightedId: null,
  highlight: () => {},
})

const HIGHLIGHT_MS = 2000

/**
 * Tracks the most recently created breadcrumb so its card can flash on entry.
 * Lives at the theme-editor level so both top-level adds and nested replies
 * (whose forms sit deep in the BreadcrumbItem recursion) can signal without
 * prop-drilling through the tree.
 */
export function HighlightProvider({ children }: { children: React.ReactNode }) {
  const [highlightedId, setHighlightedId] = useState<number | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout>>(null)

  const highlight = useCallback((id: number) => {
    setHighlightedId(id)
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setHighlightedId(null), HIGHLIGHT_MS)
  }, [])

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [])

  return (
    <HighlightContext value={{ highlightedId, highlight }}>
      {children}
    </HighlightContext>
  )
}

// eslint-disable-next-line react-refresh/only-export-components -- hook colocated with its provider
export function useHighlight() {
  return useContext(HighlightContext)
}
