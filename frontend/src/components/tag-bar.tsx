import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { fetchTags } from "@/lib/api"
import type { StreamSearch, TagWithCount } from "@/lib/types"
import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import { TagSheet } from "@/components/tag-sheet"

const VISIBLE_COUNT = 15
const MOBILE_VISIBLE_COUNT = 12

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
      <HorizontalTagBar
        sortedTags={sortedTags}
        activeTag={activeTag}
      />
    )
  }

  return (
    <VerticalTagList
      sortedTags={sortedTags}
      maxCount={maxCount}
      activeTag={activeTag}
    />
  )
}

function TagPill({
  tag,
  isActive,
}: {
  tag: TagWithCount
  isActive: boolean
}) {
  return (
    <Link
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
}

function HorizontalTagBar({
  sortedTags,
  activeTag,
}: {
  sortedTags: TagWithCount[]
  activeTag?: string
}) {
  const [sheetOpen, setSheetOpen] = useState(false)

  const needsTruncation = sortedTags.length > MOBILE_VISIBLE_COUNT
  const activeIndex = sortedTags.findIndex((t) => t.name === activeTag)
  const activeInHidden = needsTruncation && activeIndex >= MOBILE_VISIBLE_COUNT

  let mobileTags: TagWithCount[]
  if (!needsTruncation) {
    mobileTags = sortedTags
  } else if (activeInHidden) {
    mobileTags = [
      ...sortedTags.slice(0, MOBILE_VISIBLE_COUNT - 1),
      sortedTags[activeIndex],
    ]
  } else {
    mobileTags = sortedTags.slice(0, MOBILE_VISIBLE_COUNT)
  }

  const hiddenCount = sortedTags.length - mobileTags.length

  return (
    <>
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
          All
        </Link>
        {mobileTags.map((tag) => (
          <TagPill key={tag.id} tag={tag} isActive={activeTag === tag.name} />
        ))}
        {hiddenCount > 0 && (
          <button
            type="button"
            onClick={() => setSheetOpen(true)}
            className="shrink-0 rounded-full px-3 py-1.5 text-sm whitespace-nowrap bg-secondary text-muted-foreground hover:text-foreground transition-colors border border-dashed border-border cursor-pointer"
          >
            +{hiddenCount} more
          </button>
        )}
      </nav>
      {needsTruncation && (
        <TagSheet
          open={sheetOpen}
          onOpenChange={setSheetOpen}
          sortedTags={sortedTags}
          activeTag={activeTag}
        />
      )}
    </>
  )
}

function TagLink({
  tag,
  isActive,
  tier,
}: {
  tag: TagWithCount
  isActive: boolean
  tier: number
}) {
  return (
    <Link
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
}

function ToggleButton({
  onClick,
  children,
}: {
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="block w-full text-left text-xs text-muted-foreground/50 hover:text-muted-foreground border-t border-border mt-2 pt-2 cursor-pointer transition-colors"
    >
      {children}
    </button>
  )
}

function VerticalTagList({
  sortedTags,
  maxCount,
  activeTag,
}: {
  sortedTags: TagWithCount[]
  maxCount: number
  activeTag?: string
}) {
  const [expanded, setExpanded] = useState(false)
  const [filter, setFilter] = useState("")

  const hasOverflow = sortedTags.length > VISIBLE_COUNT
  const showFilter = sortedTags.length > 50
  const activeInOverflow =
    hasOverflow &&
    sortedTags.findIndex((t) => t.name === activeTag) >= VISIBLE_COUNT
  const showAll = expanded || activeInOverflow

  // When filter is active, show all matching tags flat (no overflow split)
  const filteredTags = filter
    ? sortedTags.filter((t) => t.name.startsWith(filter.toLowerCase()))
    : null

  let visibleTags: TagWithCount[]
  if (filteredTags) {
    visibleTags = filteredTags
  } else if (hasOverflow && !showAll) {
    visibleTags = sortedTags.slice(0, VISIBLE_COUNT)
  } else {
    visibleTags = sortedTags
  }

  const hiddenCount = filteredTags ? 0 : sortedTags.length - visibleTags.length

  return (
    <nav className="text-sm max-h-[calc(100vh-4rem)] overflow-y-auto scrollbar-none">
      {showFilter && (
        <Input
          placeholder="Filter tags…"
          className="h-7 text-xs mb-2"
          value={filter}
          onChange={(e) => {
            setFilter(e.target.value)
            setExpanded(false)
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setFilter("")
              ;(e.target as HTMLInputElement).blur()
            }
          }}
        />
      )}
      <Link
        to="/"
        search={(prev: StreamSearch) => ({ q: prev.q })}
        aria-current={!activeTag ? "page" : undefined}
        className={cn(
          "block py-0.5 mb-2 no-underline hover:text-foreground transition-colors",
          !activeTag
            ? "text-foreground font-medium"
            : "text-muted-foreground",
        )}
      >
        All
      </Link>
      {expanded && hasOverflow && !filteredTags && (
        <ToggleButton onClick={() => setExpanded(false)}>
          − fewer tags
        </ToggleButton>
      )}
      <div className="space-y-1 border-t border-border pt-2">
        {visibleTags.map((tag) => (
          <TagLink
            key={tag.id}
            tag={tag}
            isActive={activeTag === tag.name}
            tier={getUsageTier(tag.theme_count, maxCount)}
          />
        ))}

        {hiddenCount > 0 && (
          <ToggleButton onClick={() => setExpanded(true)}>
            + {hiddenCount} more tags
          </ToggleButton>
        )}

        {expanded && hasOverflow && !filteredTags && (
          <ToggleButton onClick={() => setExpanded(false)}>
            − fewer tags
          </ToggleButton>
        )}

        {filteredTags && filteredTags.length === 0 && (
          <p className="text-xs text-muted-foreground italic py-1">
            No matching tags.
          </p>
        )}
      </div>
    </nav>
  )
}
