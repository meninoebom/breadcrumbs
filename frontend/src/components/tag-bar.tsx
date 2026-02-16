import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { fetchTags } from "@/lib/api"
import type { StreamSearch } from "@/lib/types"
import { cn } from "@/lib/utils"

interface TagBarProps {
  activeTag?: string
  horizontal?: boolean
}

/**
 * 5 visual tiers from lightest (least used) to darkest (most used).
 * Each tier maps to a Tailwind text color class that works across
 * light and dark themes via the CSS variable system.
 */
const USAGE_TIER_CLASSES = [
  "text-muted-foreground",
  "text-foreground/70",
  "text-foreground/80",
  "text-foreground/90",
  "text-foreground",
] as const

/** Assign a tag to one of 5 tiers based on its count relative to the max. */
function getUsageTier(count: number, maxCount: number): number {
  if (maxCount === 0) return 0
  const ratio = count / maxCount
  if (ratio > 0.8) return 4
  if (ratio > 0.6) return 3
  if (ratio > 0.4) return 2
  if (ratio > 0.2) return 1
  return 0
}

export function TagBar({ activeTag, horizontal = false }: TagBarProps) {
  const { data: tags, error } = useQuery({
    queryKey: ["tags"],
    queryFn: fetchTags,
  })

  const sortedTags = useMemo(
    () =>
      tags
        ?.slice()
        .sort(
          (a, b) =>
            b.theme_count - a.theme_count || a.name.localeCompare(b.name),
        ),
    [tags],
  )

  const maxCount = useMemo(
    () => sortedTags?.reduce((max, t) => Math.max(max, t.theme_count), 0) ?? 0,
    [sortedTags],
  )

  if (error) {
    console.error("Failed to load tags:", error.message)
    return (
      <p className="text-xs text-muted-foreground italic">
        Could not load tags.
      </p>
    )
  }

  if (!sortedTags) return null
  if (sortedTags.length === 0)
    return (
      <p className="text-xs text-muted-foreground italic">No tags yet.</p>
    )

  if (horizontal) {
    return (
      <nav className="flex gap-2 overflow-x-auto pb-2 scrollbar-none text-sm">
        <Link
          to="/"
          search={(prev: StreamSearch) => ({ q: prev.q })}
          aria-current={!activeTag ? "page" : undefined}
          className={cn(
            "shrink-0 rounded-full px-3 py-1.5 no-underline transition-colors whitespace-nowrap",
            !activeTag
              ? "bg-foreground text-background font-medium"
              : "bg-secondary text-muted-foreground hover:text-foreground",
          )}
        >
          all
        </Link>
        {sortedTags.map((tag) => {
          const isActive = activeTag === tag.name
          return (
            <Link
              key={tag.id}
              to="/"
              search={(prev: StreamSearch) => ({ q: prev.q, tag: tag.name })}
              aria-label={`${tag.name}, ${tag.theme_count} ${tag.theme_count === 1 ? "theme" : "themes"}`}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "shrink-0 rounded-full px-3 py-1.5 no-underline transition-colors whitespace-nowrap",
                isActive
                  ? "bg-foreground text-background font-medium"
                  : "bg-secondary text-muted-foreground hover:text-foreground",
              )}
            >
              {tag.name}
            </Link>
          )
        })}
      </nav>
    )
  }

  return (
    <nav className="space-y-1 text-sm">
      <Link
        to="/"
        search={(prev: StreamSearch) => ({ q: prev.q })}
        aria-current={!activeTag ? "page" : undefined}
        className={cn(
          "block py-0.5 no-underline hover:text-foreground transition-colors",
          !activeTag
            ? "text-foreground font-medium"
            : "text-muted-foreground",
        )}
      >
        all
      </Link>
      {sortedTags.map((tag) => {
        const isActive = activeTag === tag.name
        const tier = getUsageTier(tag.theme_count, maxCount)
        return (
          <Link
            key={tag.id}
            to="/"
            search={(prev: StreamSearch) => ({ q: prev.q, tag: tag.name })}
            aria-label={`${tag.name}, ${tag.theme_count} ${tag.theme_count === 1 ? "theme" : "themes"}`}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "block truncate py-0.5 no-underline hover:text-foreground transition-colors",
              isActive ? "text-foreground font-medium" : USAGE_TIER_CLASSES[tier],
            )}
          >
            {tag.name}
          </Link>
        )
      })}
    </nav>
  )
}
