import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { X } from "lucide-react"
import { ThemeSection } from "@/components/theme-section"
import { TagBar } from "@/components/tag-bar"
import { StreamSkeleton } from "@/components/stream-skeleton"
import { WeeklySummary } from "@/components/weekly-summary"
import { CollapsedMonthCard } from "@/components/collapsed-month-card"
import { DigestNav } from "@/components/digest-nav"
import { fetchDigests, fetchMonths, fetchThemes } from "@/lib/api"
import { buildFeed } from "@/lib/feed"
import type { MonthSummary, StreamSearch } from "@/lib/types"
import { formatDateHeading } from "@/lib/utils"

const EXPANDED_WINDOW_DAYS = 31

export const Route = createFileRoute("/")({
  component: ReaderStream,
  validateSearch: (search: Record<string, unknown>): StreamSearch => ({
    tag: typeof search.tag === "string" ? search.tag : undefined,
    q: typeof search.q === "string" ? search.q : undefined,
    open: typeof search.open === "string" ? search.open : undefined,
  }),
})

function rollingCutoffDate(): string {
  const d = new Date()
  d.setUTCDate(d.getUTCDate() - EXPANDED_WINDOW_DAYS)
  return d.toISOString().slice(0, 10)
}

/**
 * The earliest date whose themes belong in the expanded feed.
 *
 * If any months are collapsed, the expanded region starts on day 1 of the
 * month immediately after the newest collapsed month. This keeps months
 * that straddle the 31-day window fully visible (e.g. themes from earlier
 * in March when today is late April).
 */
function expandedSinceDate(months: MonthSummary[]): string {
  if (months.length === 0) return rollingCutoffDate()
  // months is sorted newest-first from the API. JS Date handles Dec→Jan.
  const newest = months[0]
  return new Date(Date.UTC(newest.year, newest.month, 1))
    .toISOString()
    .slice(0, 10)
}

function ReaderStream() {
  const { tag, q, open } = Route.useSearch()
  const navigate = useNavigate()
  const isFiltered = Boolean(tag || q)

  const { data: months } = useQuery({
    queryKey: ["months"],
    queryFn: () => fetchMonths(),
    enabled: !isFiltered,
  })

  // `since` depends on the months response: expanded feed starts on the
  // first day after the newest collapsed month. Wait for months before
  // firing the themes query (unless we're in a filtered view, which
  // ignores the window entirely).
  const since = months === undefined ? undefined : expandedSinceDate(months)

  const { data: themes, isLoading, error } = useQuery({
    queryKey: isFiltered
      ? ["themes", { visibility: "published", tag, q }]
      : ["themes", { visibility: "published", since }],
    queryFn: () =>
      fetchThemes(
        isFiltered
          ? { visibility: "published", tag, q }
          : { visibility: "published", since },
      ),
    enabled: isFiltered || since !== undefined,
  })

  const { data: digests } = useQuery({
    queryKey: ["digests"],
    queryFn: () => fetchDigests(),
    enabled: !isFiltered,
  })

  const openKeys = new Set(open?.split(",").filter(Boolean) ?? [])
  const collapsedMonthKeys = new Set(
    (months ?? []).map((m) => monthKey(m)),
  )
  const feed = buildFeed(themes ?? [], digests ?? [], collapsedMonthKeys)

  const toggleMonth = (key: string) => {
    const next = new Set(openKeys)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    navigate({
      to: "/",
      search: (prev) => ({
        ...prev,
        open: next.size === 0 ? undefined : Array.from(next).join(","),
      }),
    })
  }

  return (
    <div className="flex flex-col md:flex-row gap-6 md:gap-10">
      <div className="md:hidden sticky top-0 z-10 bg-background pt-2 pb-1">
        <TagBar activeTag={tag} horizontal />
      </div>

      <aside className="hidden md:block w-40 shrink-0 sticky top-8 self-start space-y-6">
        <div>
          <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground/60 mb-3">
            Tags
          </h3>
          <TagBar activeTag={tag} />
        </div>
        <DigestNav digests={digests ?? []} />
      </aside>

      <div className="flex-1 min-w-0 space-y-6">
        {isFiltered && <ActiveFilters tag={tag} q={q} />}

        {isLoading && <StreamSkeleton />}

        {error && <p className="text-destructive">Error: {error.message}</p>}

        {themes && themes.length === 0 && !isFiltered && (!months || months.length === 0) && (
          <div className="py-12 text-center space-y-2">
            <p className="text-muted-foreground italic">
              The trail is quiet. No breadcrumbs have been dropped here yet.
            </p>
          </div>
        )}

        {themes && themes.length === 0 && isFiltered && (
          <div className="py-12 text-center space-y-2">
            <p className="text-muted-foreground italic">
              No breadcrumbs along this path.
            </p>
          </div>
        )}

        {feed.length > 0 && (
          <div className="space-y-10">
            {feed.map((item) =>
              item.kind === "date-group" ? (
                <section key={item.key}>
                  <h2 className="text-xl font-semibold tracking-tight mb-6">
                    {formatDateHeading(item.themes[0].created_at)}
                  </h2>
                  <div className="space-y-8 pl-4 border-l-2 border-border">
                    {item.themes.map((theme) => (
                      <ThemeSection key={theme.id} theme={theme} />
                    ))}
                  </div>
                </section>
              ) : (
                <WeeklySummary key={item.key} digest={item.digest} />
              ),
            )}
          </div>
        )}

        {!isFiltered && months && months.length > 0 && (
          <div className="space-y-4 pt-4">
            {months.map((m) => {
              const key = monthKey(m)
              return (
                <CollapsedMonthCard
                  key={key}
                  month={m}
                  digests={digests ?? []}
                  isOpen={openKeys.has(key)}
                  onToggle={() => toggleMonth(key)}
                />
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

function monthKey(m: MonthSummary): string {
  return `${m.year}-${String(m.month).padStart(2, "0")}`
}

function ActiveFilters({ tag, q }: { tag?: string; q?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <span>Showing:</span>
      {tag && (
        <span className="inline-flex items-center gap-1 rounded-md bg-secondary px-2 py-0.5">
          tag: {tag}
          <Link
            to="/"
            search={(prev: StreamSearch) => ({ q: prev.q })}
            className="hover:text-foreground p-1"
          >
            <X className="size-3" />
          </Link>
        </span>
      )}
      {q && (
        <span className="inline-flex items-center gap-1 rounded-md bg-secondary px-2 py-0.5">
          search: &ldquo;{q}&rdquo;
          <Link
            to="/"
            search={(prev: StreamSearch) => ({ tag: prev.tag })}
            className="hover:text-foreground p-1"
          >
            <X className="size-3" />
          </Link>
        </span>
      )}
    </div>
  )
}
