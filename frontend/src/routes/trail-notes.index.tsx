import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { fetchDigests } from "@/lib/api"
import type { DigestPublic } from "@/lib/types"

export const Route = createFileRoute("/trail-notes/")({
  component: TrailNotesArchive,
})

/** Group digests by year. */
function groupByYear(digests: DigestPublic[]): [string, DigestPublic[]][] {
  const groups = new Map<string, DigestPublic[]>()
  for (const d of digests) {
    const year = d.period_start.slice(0, 4)
    const list = groups.get(year)
    if (list) list.push(d)
    else groups.set(year, [d])
  }
  return Array.from(groups.entries())
}

function formatDigestDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00")
  return new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric" }).format(d)
}

function TrailNotesArchive() {
  const { data: digests, isLoading, error } = useQuery({
    queryKey: ["digests"],
    queryFn: () => fetchDigests(),
  })

  const yearGroups = digests ? groupByYear(digests) : []

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">Trail Notes</h1>
        <p className="text-sm text-muted-foreground italic">
          A weekly letter of what surfaced here.
        </p>
      </div>

      {isLoading && (
        <div className="space-y-3 animate-pulse">
          <div className="h-4 bg-muted rounded w-16" />
          <div className="h-4 bg-muted rounded w-3/4" />
          <div className="h-4 bg-muted rounded w-2/3" />
        </div>
      )}

      {error && <p className="text-destructive">Error: {error.message}</p>}

      {digests && digests.length === 0 && (
        <p className="text-muted-foreground italic py-8">
          No trail notes yet. The first one is on its way.
        </p>
      )}

      {yearGroups.map(([year, items]) => (
        <section key={year} className="space-y-1">
          <h2 className="text-lg font-semibold tracking-tight text-muted-foreground mb-3">
            {year}
          </h2>
          {items.map((digest) => (
            <Link
              key={digest.id}
              to="/trail-notes/$digestId"
              params={{ digestId: String(digest.id) }}
              className="flex items-baseline gap-4 py-2 group no-underline"
            >
              <span className="text-sm text-muted-foreground tabular-nums shrink-0">
                {formatDigestDate(digest.period_start)}
              </span>
              <span className="text-sm group-hover:text-foreground transition-colors truncate">
                {digest.title}
              </span>
              <span className="text-muted-foreground/40 text-sm ml-auto shrink-0">→</span>
            </Link>
          ))}
        </section>
      ))}
    </div>
  )
}
