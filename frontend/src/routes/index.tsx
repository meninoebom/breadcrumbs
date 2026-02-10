import { createFileRoute } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { ThemeSection } from "@/components/theme-section"
import { fetchThemes } from "@/lib/api"

interface StreamSearch {
  tag?: string
}

export const Route = createFileRoute("/")({
  component: ReaderStream,
  validateSearch: (search: Record<string, unknown>): StreamSearch => ({
    tag: typeof search.tag === "string" ? search.tag : undefined,
  }),
})

function ReaderStream() {
  const { data: themes, isLoading, error } = useQuery({
    queryKey: ["themes", { visibility: "published" }],
    queryFn: () => fetchThemes({ visibility: "published" }),
  })

  if (isLoading) return <StreamSkeleton />

  if (error) {
    return <p className="text-destructive">Error: {error.message}</p>
  }

  if (!themes || themes.length === 0) {
    return (
      <div className="py-12 text-center space-y-2">
        <p className="text-muted-foreground">No published themes yet.</p>
        <p className="text-sm text-muted-foreground">
          When themes are published, they'll appear here as a continuous stream.
        </p>
      </div>
    )
  }

  return (
    <div>
      {themes.map((theme, index) => (
        <div key={theme.id}>
          {index > 0 && <hr className="my-8 border-border" />}
          <ThemeSection theme={theme} />
        </div>
      ))}
    </div>
  )
}

function StreamSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-6 bg-muted rounded w-1/3" />
      <div className="h-4 bg-muted rounded w-2/3" />
      <div className="h-4 bg-muted rounded w-1/2" />
      <div className="h-4 bg-muted rounded w-3/4" />
    </div>
  )
}
