import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { X } from "lucide-react"
import { ThemeSection } from "@/components/theme-section"
import { TagBar } from "@/components/tag-bar"
import { StreamSkeleton } from "@/components/stream-skeleton"
import { fetchThemes } from "@/lib/api"
import type { StreamSearch } from "@/lib/types"

export const Route = createFileRoute("/")({
  component: ReaderStream,
  validateSearch: (search: Record<string, unknown>): StreamSearch => ({
    tag: typeof search.tag === "string" ? search.tag : undefined,
    q: typeof search.q === "string" ? search.q : undefined,
  }),
})

function ReaderStream() {
  const { tag, q } = Route.useSearch()

  const { data: themes, isLoading, error } = useQuery({
    queryKey: ["themes", { visibility: "published", tag, q }],
    queryFn: () => fetchThemes({ visibility: "published", tag, q }),
  })

  return (
    <div className="space-y-6">
      <TagBar activeTag={tag} />

      {(tag || q) && <ActiveFilters tag={tag} q={q} />}

      {isLoading && <StreamSkeleton />}

      {error && <p className="text-destructive">Error: {error.message}</p>}

      {themes && themes.length === 0 && (
        <div className="py-12 text-center space-y-2">
          <p className="text-muted-foreground">
            {tag || q ? "No themes match your filters." : "No published themes yet."}
          </p>
          {!tag && !q && (
            <p className="text-sm text-muted-foreground">
              When themes are published, they'll appear here as a continuous
              stream.
            </p>
          )}
        </div>
      )}

      {themes && themes.length > 0 && (
        <div>
          {themes.map((theme, index) => (
            <div key={theme.id}>
              {index > 0 && <hr className="my-8 border-border" />}
              <ThemeSection theme={theme} />
            </div>
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
