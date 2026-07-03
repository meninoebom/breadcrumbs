import { useEffect, useRef, useState } from "react"

/**
 * Returns a ref and a boolean indicating whether the element has scrolled
 * into view. Once revealed, stays true (no re-hiding).
 */
export function useScrollReveal<T extends HTMLElement = HTMLDivElement>() {
  const ref = useRef<T>(null)
  const prefersReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  const [revealed, setRevealed] = useState(prefersReducedMotion)

  useEffect(() => {
    if (prefersReducedMotion) return

    const el = ref.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setRevealed(true)
          observer.disconnect()
        }
      },
      { threshold: 0.1 },
    )

    observer.observe(el)
    return () => observer.disconnect()
  }, [prefersReducedMotion])

  return { ref, revealed }
}
