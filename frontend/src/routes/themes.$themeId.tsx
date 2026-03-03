import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft } from "lucide-react"
import { fetchTheme } from "@/lib/api"
import { ThemeSection } from "@/components/theme-section"

export const Route = createFileRoute("/themes/$themeId")({
  component: ThemePermalink,
})

const BackLink = () => (
  <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
    <ArrowLeft className="h-3.5 w-3.5" />
    Back to feed
  </Link>
)

function ThemePermalink() {
  const { themeId } = Route.useParams()
  const id = Number(themeId)
  const isValidId = Number.isInteger(id) && id > 0

  const { data: theme, isLoading, error } = useQuery({
    queryKey: ["themes", id],
    queryFn: () => fetchTheme(id),
    enabled: isValidId,
  })

  if (!isValidId) {
    return (
      <div className="max-w-2xl mx-auto space-y-4 py-12 text-center">
        <p className="text-destructive">This theme link is invalid.</p>
        <BackLink />
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto animate-pulse space-y-3">
        <div className="h-4 bg-muted rounded w-full" />
        <div className="h-4 bg-muted rounded w-3/4" />
      </div>
    )
  }

  if (error || !theme) {
    return (
      <div className="max-w-2xl mx-auto space-y-4 py-12 text-center">
        <p className="text-destructive">
          {error?.message?.includes("404")
            ? "This theme could not be found."
            : "Failed to load theme."}
        </p>
        <BackLink />
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <BackLink />
      <ThemeSection theme={theme} />
    </div>
  )
}
