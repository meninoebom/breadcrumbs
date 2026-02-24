import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import Markdown from "react-markdown"
import { fetchDigest, fetchDigests } from "@/lib/api"
import { SubscribeWidget } from "@/components/subscribe-widget"

export const Route = createFileRoute("/trail-notes/$digestId")({
  component: TrailNoteDetail,
})

function formatWeekRange(start: string, end: string): string {
  const s = new Date(start + "T00:00:00")
  const e = new Date(end + "T00:00:00")
  const fmt = new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric", year: "numeric" })
  return `${fmt.format(s)} — ${fmt.format(e)}`
}

function TrailNoteDetail() {
  const { digestId } = Route.useParams()

  const { data: digest, isLoading, error } = useQuery({
    queryKey: ["digests", digestId],
    queryFn: () => fetchDigest(Number(digestId)),
  })

  // Fetch siblings for prev/next nav
  const { data: allDigests } = useQuery({
    queryKey: ["digests"],
    queryFn: () => fetchDigests(),
  })

  const currentIndex = allDigests?.findIndex((d) => d.id === Number(digestId)) ?? -1
  const prev = currentIndex > 0 ? allDigests?.[currentIndex - 1] : undefined
  const next = allDigests && currentIndex < allDigests.length - 1
    ? allDigests[currentIndex + 1]
    : undefined

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto space-y-4 animate-pulse">
        <div className="h-6 bg-muted rounded w-2/3" />
        <div className="h-4 bg-muted rounded w-1/3" />
        <div className="h-4 bg-muted rounded w-full" />
        <div className="h-4 bg-muted rounded w-5/6" />
      </div>
    )
  }

  if (error) {
    return <p className="text-destructive max-w-2xl mx-auto">Error: {error.message}</p>
  }

  if (!digest) return null

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div className="space-y-1">
        <Link
          to="/trail-notes"
          className="text-sm text-muted-foreground hover:text-foreground no-underline"
        >
          ← Trail Notes
        </Link>
        <h1 className="text-2xl font-bold tracking-tight">{digest.title}</h1>
        <p className="text-sm text-muted-foreground">
          {formatWeekRange(digest.period_start, digest.period_end)}
        </p>
      </div>

      <article className="prose prose-sm max-w-none">
        <Markdown>{digest.summary_md}</Markdown>
      </article>

      {/* Prev / Next navigation */}
      <nav className="flex justify-between items-center pt-4 border-t">
        {next ? (
          <Link
            to="/trail-notes/$digestId"
            params={{ digestId: String(next.id) }}
            className="text-sm text-muted-foreground hover:text-foreground no-underline"
          >
            ← {next.title}
          </Link>
        ) : (
          <span />
        )}
        {prev ? (
          <Link
            to="/trail-notes/$digestId"
            params={{ digestId: String(prev.id) }}
            className="text-sm text-muted-foreground hover:text-foreground no-underline"
          >
            {prev.title} →
          </Link>
        ) : (
          <span />
        )}
      </nav>

      <SubscribeWidget />
    </div>
  )
}
