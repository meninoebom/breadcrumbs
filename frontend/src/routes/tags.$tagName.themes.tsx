import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { ThemeSection } from "@/components/theme-section"
import { StreamSkeleton } from "@/components/stream-skeleton"
import { fetchThemesByTag } from "@/lib/api"

export const Route = createFileRoute("/tags/$tagName/themes")({
  component: TagThemesPage,
})

function TagThemesPage() {
  const { tagName } = Route.useParams()

  const { data: themes, isLoading, error } = useQuery({
    queryKey: ["tags", tagName, "themes"],
    queryFn: () => fetchThemesByTag(tagName),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link
          to="/"
          className="text-sm text-muted-foreground hover:text-foreground no-underline"
        >
          &larr; All themes
        </Link>
        <h2 className="text-lg font-semibold">
          Themes tagged &ldquo;{tagName}&rdquo;
        </h2>
      </div>

      {isLoading && <StreamSkeleton />}

      {error && <p className="text-destructive">Error: {error.message}</p>}

      {themes && themes.length === 0 && (
        <p className="text-muted-foreground">No themes found for this tag.</p>
      )}

      {themes &&
        themes.length > 0 &&
        themes.map((theme, index) => (
          <div key={theme.id}>
            {index > 0 && <hr className="my-8 border-border" />}
            <ThemeSection theme={theme} />
          </div>
        ))}
    </div>
  )
}
