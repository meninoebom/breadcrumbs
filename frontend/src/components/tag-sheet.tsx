import { useMemo, useState } from "react"
import { Link } from "@tanstack/react-router"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import type { StreamSearch, TagWithCount } from "@/lib/types"
import { cn } from "@/lib/utils"

const POPULAR_COUNT = 10
const SEARCH_THRESHOLD = 40

interface TagSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sortedTags: TagWithCount[]
  activeTag?: string
}

export function TagSheet({
  open,
  onOpenChange,
  sortedTags,
  activeTag,
}: TagSheetProps) {
  const [filter, setFilter] = useState("")

  const showSearch = sortedTags.length >= SEARCH_THRESHOLD

  const popularTags = useMemo(
    () => sortedTags.slice(0, POPULAR_COUNT),
    [sortedTags],
  )

  const alphabeticalTags = useMemo(
    () => [...sortedTags].sort((a, b) => a.name.localeCompare(b.name)),
    [sortedTags],
  )

  const filteredTags = filter
    ? alphabeticalTags.filter((t) =>
        t.name.includes(filter.toLowerCase()),
      )
    : null

  function handleOpenChange(next: boolean) {
    onOpenChange(next)
    if (!next) setFilter("")
  }

  function handleSelect() {
    handleOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        className="fixed bottom-0 left-0 top-auto translate-x-0 translate-y-0 w-full max-w-full rounded-t-xl rounded-b-none max-h-[70vh] flex flex-col sm:max-w-full"
      >
        <DialogHeader>
          <DialogTitle className="text-base">Browse Tags</DialogTitle>
        </DialogHeader>

        {showSearch && (
          <Input
            placeholder="Search tags…"
            className="h-8 text-sm"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") {
                setFilter("")
                ;(e.target as HTMLInputElement).blur()
              }
            }}
          />
        )}

        <div className="overflow-y-auto flex-1 -mx-6 px-6">
          {filteredTags !== null ? (
            <FilteredTagList
              tags={filteredTags}
              activeTag={activeTag}
              onSelect={handleSelect}
            />
          ) : (
            <BrowseTagSections
              popularTags={popularTags}
              alphabeticalTags={alphabeticalTags}
              activeTag={activeTag}
              onSelect={handleSelect}
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function FilteredTagList({
  tags,
  activeTag,
  onSelect,
}: {
  tags: TagWithCount[]
  activeTag?: string
  onSelect: () => void
}) {
  if (tags.length === 0) {
    return (
      <p className="text-sm text-muted-foreground italic py-4">
        No matching tags.
      </p>
    )
  }

  return (
    <div className="space-y-1 py-2">
      {tags.map((tag) => (
        <SheetTagRow
          key={tag.id}
          tag={tag}
          isActive={activeTag === tag.name}
          onClick={onSelect}
        />
      ))}
    </div>
  )
}

function BrowseTagSections({
  popularTags,
  alphabeticalTags,
  activeTag,
  onSelect,
}: {
  popularTags: TagWithCount[]
  alphabeticalTags: TagWithCount[]
  activeTag?: string
  onSelect: () => void
}) {
  return (
    <>
      <section className="py-2">
        <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground/60 mb-2">
          Popular
        </h3>
        <div className="space-y-1">
          {popularTags.map((tag) => (
            <SheetTagRow
              key={tag.id}
              tag={tag}
              isActive={activeTag === tag.name}
              showCount
              onClick={onSelect}
            />
          ))}
        </div>
      </section>

      <div className="border-t border-border my-2" />

      <section className="py-2">
        <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground/60 mb-2">
          All
        </h3>
        <div className="space-y-1">
          {alphabeticalTags.map((tag) => (
            <SheetTagRow
              key={tag.id}
              tag={tag}
              isActive={activeTag === tag.name}
              showCount
              onClick={onSelect}
            />
          ))}
        </div>
      </section>
    </>
  )
}

function SheetTagRow({
  tag,
  isActive,
  showCount = false,
  onClick,
}: {
  tag: TagWithCount
  isActive: boolean
  showCount?: boolean
  onClick: () => void
}) {
  return (
    <Link
      to="/"
      search={(prev: StreamSearch) => ({ q: prev.q, tag: tag.name })}
      onClick={onClick}
      aria-current={isActive ? "page" : undefined}
      className={cn(
        "flex items-center justify-between py-1.5 px-2 rounded-md no-underline transition-colors text-sm",
        isActive
          ? "bg-foreground text-background font-medium"
          : "text-foreground hover:bg-secondary",
      )}
    >
      <span className="truncate">{tag.name}</span>
      {showCount && (
        <span className="text-xs text-muted-foreground ml-2 shrink-0">
          {tag.theme_count}
        </span>
      )}
    </Link>
  )
}
