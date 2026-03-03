import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { X } from "lucide-react"
import { ThemeSection } from "@/components/theme-section"
import { TagBar } from "@/components/tag-bar"
import { StreamSkeleton } from "@/components/stream-skeleton"
import { WeeklySummary } from "@/components/weekly-summary"
import { DigestNav } from "@/components/digest-nav"
import { fetchDigests, fetchThemes } from "@/lib/api"
import type { DigestPublic, StreamSearch, ThemePublic } from "@/lib/types"
import { dateKey, formatDateHeading } from "@/lib/utils"

export const Route = createFileRoute("/")({
  component: ReaderStream,
  validateSearch: (search: Record<string, unknown>): StreamSearch => ({
    tag: typeof search.tag === "string" ? search.tag : undefined,
    q: typeof search.q === "string" ? search.q : undefined,
  }),
})

type FeedItem =
  | { kind: "date-group"; key: string; date: string; themes: ThemePublic[] }
  | { kind: "weekly-summary"; key: string; date: string; digest: DigestPublic }

/**
 * Merge date-grouped themes and weekly digests into a single
 * chronologically sorted feed (newest first).
 */
function buildFeed(themes: ThemePublic[], digests: DigestPublic[]): FeedItem[] {
  const items: FeedItem[] = []

  // Group themes by date
  const groups = new Map<string, ThemePublic[]>()
  for (const theme of themes) {
    const key = dateKey(theme.created_at)
    const list = groups.get(key)
    if (list) list.push(theme)
    else groups.set(key, [theme])
  }

  for (const [key, groupThemes] of groups) {
    items.push({
      kind: "date-group",
      key,
      date: key,
      themes: groupThemes,
    })
  }

  // Add digests keyed by their period_end (so they appear after that week's content)
  for (const digest of digests) {
    items.push({
      kind: "weekly-summary",
      key: `summary-${digest.id}`,
      date: digest.period_end,
      digest,
    })
  }

  // Sort newest first
  items.sort((a, b) => b.date.localeCompare(a.date))

  return items
}

function ReaderStream() {
  const { tag, q } = Route.useSearch()

  const { data: themes, isLoading, error } = useQuery({
    queryKey: ["themes", { visibility: "published", tag, q }],
    queryFn: () => fetchThemes({ visibility: "published", tag, q }),
  })

  // Only fetch digests when not filtering
  const { data: digests } = useQuery({
    queryKey: ["digests"],
    queryFn: () => fetchDigests(),
    enabled: !tag && !q,
  })

  const feed = buildFeed(themes ?? [], digests ?? [])

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
        {(tag || q) && <ActiveFilters tag={tag} q={q} />}

        {isLoading && <StreamSkeleton />}

        {error && <p className="text-destructive">Error: {error.message}</p>}

        {themes && themes.length === 0 && (
          <div className="py-12 text-center space-y-2">
            <p className="text-muted-foreground italic">
              {tag || q
                ? "No breadcrumbs along this path."
                : "The trail is quiet. No breadcrumbs have been dropped here yet."}
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
      </div>
    </div>
  )
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
