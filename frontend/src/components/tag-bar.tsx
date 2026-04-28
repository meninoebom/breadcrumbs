import { useMemo, useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import {
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core"
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
  horizontalListSortingStrategy,
} from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { GripVertical } from "lucide-react"
import { fetchTags, reorderTags } from "@/lib/api"
import { isAuthenticated } from "@/lib/auth"
import type { StreamSearch, TagWithCount } from "@/lib/types"
import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import { TagSheet } from "@/components/tag-sheet"

const VISIBLE_COUNT = 15
const MOBILE_VISIBLE_COUNT = 12
const SORT_STORAGE_KEY = "breadcrumbs-tag-sort"

type TagSortOrder = "usage" | "alpha" | "custom"

function getStoredSort(): TagSortOrder {
  try {
    const v = localStorage.getItem(SORT_STORAGE_KEY)
    if (v === "alpha" || v === "usage" || v === "custom") return v
    return "custom"
  } catch {
    return "custom"
  }
}

function storeSort(order: TagSortOrder) {
  try {
    localStorage.setItem(SORT_STORAGE_KEY, order)
  } catch {
    // ignore
  }
}

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
  const [sortOrder, setSortOrder] = useState<TagSortOrder>(getStoredSort)
  const queryClient = useQueryClient()

  const { data: tags, error } = useQuery({
    queryKey: ["tags"],
    queryFn: fetchTags,
  })

  // Local ordered state for optimistic drag reorder
  const [localOrder, setLocalOrder] = useState<number[] | null>(null)

  const sortedTags = useMemo(() => {
    if (!tags) return undefined
    const base = tags.slice()

    if (sortOrder === "custom") {
      if (localOrder) {
        const idToTag = new Map(tags.map((t) => [t.id, t]))
        const ordered = localOrder.flatMap((id) => {
          const t = idToTag.get(id)
          return t ? [t] : []
        })
        // append any tags not in localOrder (newly created)
        const inOrder = new Set(localOrder)
        const rest = base.filter((t) => !inOrder.has(t.id))
        return [...ordered, ...rest]
      }
      return base // server already returned in position order
    }

    return base.sort(
      sortOrder === "usage"
        ? (a, b) => b.theme_count - a.theme_count || a.name.localeCompare(b.name)
        : (a, b) => a.name.localeCompare(b.name),
    )
  }, [tags, sortOrder, localOrder])

  const maxCount = useMemo(
    () => sortedTags?.reduce((max, t) => Math.max(max, t.theme_count), 0) ?? 0,
    [sortedTags],
  )

  const canDrag = isAuthenticated() && sortOrder === "custom"

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  )

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over || active.id === over.id || !sortedTags) return

    const oldIndex = sortedTags.findIndex((t) => t.id === active.id)
    const newIndex = sortedTags.findIndex((t) => t.id === over.id)
    const reordered = arrayMove(sortedTags, oldIndex, newIndex)
    const newIds = reordered.map((t) => t.id)
    const prevOrder = localOrder

    setLocalOrder(newIds)
    reorderTags(newIds)
      .then(() => {
        setLocalOrder(null) // let server order take over after sync
        queryClient.invalidateQueries({ queryKey: ["tags"] })
      })
      .catch(() => {
        setLocalOrder(prevOrder) // roll back optimistic update on failure
      })
  }

  function cycleSortOrder() {
    const next: TagSortOrder =
      sortOrder === "custom" ? "usage" : sortOrder === "usage" ? "alpha" : "custom"
    setSortOrder(next)
    storeSort(next)
    // clear local order when leaving custom mode
    if (next !== "custom") setLocalOrder(null)
  }

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
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <HorizontalTagBar
          sortedTags={sortedTags}
          activeTag={activeTag}
          canDrag={canDrag}
        />
      </DndContext>
    )
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <VerticalTagList
        sortedTags={sortedTags}
        maxCount={maxCount}
        activeTag={activeTag}
        sortOrder={sortOrder}
        onCycleSort={cycleSortOrder}
        canDrag={canDrag}
      />
    </DndContext>
  )
}

function TagPill({
  tag,
  isActive,
  canDrag,
}: {
  tag: TagWithCount
  isActive: boolean
  canDrag: boolean
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: tag.id, disabled: !canDrag })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : undefined,
  }

  return (
    <div ref={setNodeRef} style={style} className="shrink-0 flex items-center">
      {canDrag && (
        <button
          {...attributes}
          {...listeners}
          type="button"
          className="cursor-grab active:cursor-grabbing p-0.5 text-muted-foreground/40 hover:text-muted-foreground"
          aria-label={`Drag to reorder ${tag.name}`}
        >
          <GripVertical className="h-3 w-3" />
        </button>
      )}
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
        <span className="text-[10px] opacity-50 ml-1">{tag.theme_count}</span>
      </Link>
    </div>
  )
}

function HorizontalTagBar({
  sortedTags,
  activeTag,
  canDrag,
}: {
  sortedTags: TagWithCount[]
  activeTag?: string
  canDrag: boolean
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
      <SortableContext
        items={mobileTags.map((t) => t.id)}
        strategy={horizontalListSortingStrategy}
      >
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
            <TagPill
              key={tag.id}
              tag={tag}
              isActive={activeTag === tag.name}
              canDrag={canDrag}
            />
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
      </SortableContext>
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

function SortableTagLink({
  tag,
  isActive,
  tier,
  canDrag,
}: {
  tag: TagWithCount
  isActive: boolean
  tier: number
  canDrag: boolean
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: tag.id, disabled: !canDrag })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : undefined,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-1 group"
    >
      {canDrag && (
        <button
          {...attributes}
          {...listeners}
          type="button"
          className="cursor-grab active:cursor-grabbing opacity-0 group-hover:opacity-100 text-muted-foreground/40 hover:text-muted-foreground transition-opacity shrink-0"
          aria-label={`Drag to reorder ${tag.name}`}
        >
          <GripVertical className="h-3 w-3" />
        </button>
      )}
      <Link
        to="/"
        search={(prev: StreamSearch) => ({ q: prev.q, tag: tag.name })}
        aria-label={`${tag.name}, ${tag.theme_count} ${tag.theme_count === 1 ? "theme" : "themes"}`}
        aria-current={isActive ? "page" : undefined}
        className={cn(
          "flex items-center justify-between py-0.5 no-underline hover:text-foreground transition-colors flex-1 min-w-0",
          isActive ? "text-foreground font-medium" : USAGE_TIER_CLASSES[tier],
        )}
      >
        <span className="truncate">{tag.name}</span>
        <span className="text-xs text-muted-foreground/50 ml-2 shrink-0 tabular-nums">
          {tag.theme_count}
        </span>
      </Link>
    </div>
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

const NEXT_SORT_LABEL: Record<TagSortOrder, string> = {
  custom: "# usage",  // custom → usage
  usage: "A→Z",       // usage → alpha
  alpha: "↕ custom",  // alpha → custom
}

const NEXT_SORT_TITLE: Record<TagSortOrder, string> = {
  custom: "Switch to by usage",
  usage: "Switch to alphabetical",
  alpha: "Switch to custom order",
}

function SortToggle({
  sortOrder,
  onCycle,
}: {
  sortOrder: TagSortOrder
  onCycle: () => void
}) {
  return (
    <button
      type="button"
      onClick={onCycle}
      className="text-[11px] text-muted-foreground/50 hover:text-muted-foreground cursor-pointer transition-colors"
      title={NEXT_SORT_TITLE[sortOrder]}
    >
      {NEXT_SORT_LABEL[sortOrder]}
    </button>
  )
}

function VerticalTagList({
  sortedTags,
  maxCount,
  activeTag,
  sortOrder,
  onCycleSort,
  canDrag,
}: {
  sortedTags: TagWithCount[]
  maxCount: number
  activeTag?: string
  sortOrder: TagSortOrder
  onCycleSort: () => void
  canDrag: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const [filter, setFilter] = useState("")

  const hasOverflow = sortedTags.length > VISIBLE_COUNT
  const showFilter = sortedTags.length > 50
  const activeInOverflow =
    hasOverflow &&
    sortedTags.findIndex((t) => t.name === activeTag) >= VISIBLE_COUNT
  const showAll = expanded || activeInOverflow

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
      <div className="flex items-center justify-between mb-2">
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
          All
        </Link>
        <SortToggle sortOrder={sortOrder} onCycle={onCycleSort} />
      </div>
      {expanded && hasOverflow && !filteredTags && (
        <ToggleButton onClick={() => setExpanded(false)}>
          − fewer tags
        </ToggleButton>
      )}
      <SortableContext
        items={visibleTags.map((t) => t.id)}
        strategy={verticalListSortingStrategy}
      >
        <div className="space-y-1 border-t border-border pt-2">
          {visibleTags.map((tag) => (
            <SortableTagLink
              key={tag.id}
              tag={tag}
              isActive={activeTag === tag.name}
              tier={getUsageTier(tag.theme_count, maxCount)}
              canDrag={canDrag}
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
      </SortableContext>
    </nav>
  )
}
