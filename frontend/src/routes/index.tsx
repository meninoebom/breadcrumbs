import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { X } from "lucide-react"
import { ThemeSection } from "@/components/theme-section"
import { TagBar } from "@/components/tag-bar"
import { StreamSkeleton } from "@/components/stream-skeleton"
import { fetchThemes } from "@/lib/api"
import type { StreamSearch, ThemePublic } from "@/lib/types"
import { dateKey, formatDateHeading } from "@/lib/utils"

export const Route = createFileRoute("/")({
  component: ReaderStream,
  validateSearch: (search: Record<string, unknown>): StreamSearch => ({
    tag: typeof search.tag === "string" ? search.tag : undefined,
    q: typeof search.q === "string" ? search.q : undefined,
  }),
})

/** Group themes by their created_at date, preserving order within each group. */
function groupByDate(themes: ThemePublic[]): [string, ThemePublic[]][] {
  const groups = new Map<string, ThemePublic[]>()
  for (const theme of themes) {
    const key = dateKey(theme.created_at)
    const list = groups.get(key)
    if (list) {
      list.push(theme)
    } else {
      groups.set(key, [theme])
    }
  }
  return Array.from(groups.entries())
}

function ReaderStream() {
  const { tag, q } = Route.useSearch()

  const { data: themes, isLoading, error } = useQuery({
    queryKey: ["themes", { visibility: "published", tag, q }],
    queryFn: () => fetchThemes({ visibility: "published", tag, q }),
  })

  const dateGroups = themes ? groupByDate(themes) : []

  return (
    <div className="space-y-6">
      <TagBar activeTag={tag} />

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

      {dateGroups.length > 0 && (
        <div className="space-y-10">
          {dateGroups.map(([key, groupThemes]) => (
            <section key={key}>
              <h2 className="text-xl font-semibold tracking-tight mb-6">
                {formatDateHeading(groupThemes[0].created_at)}
              </h2>

              <div className="space-y-8 pl-4 border-l-2 border-border">
                {groupThemes.map((theme) => (
                  <ThemeSection key={theme.id} theme={theme} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
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
            className="hover:text-foreground"
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
            className="hover:text-foreground"
          >
            <X className="size-3" />
          </Link>
        </span>
      )}
    </div>
  )
}
