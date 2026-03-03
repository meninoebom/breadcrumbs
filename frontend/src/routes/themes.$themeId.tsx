import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft } from "lucide-react"
import { fetchTheme } from "@/lib/api"
import { ThemeSection } from "@/components/theme-section"

export const Route = createFileRoute("/themes/$themeId")({
  component: ThemePermalink,
})

function ThemePermalink() {
  const { themeId } = Route.useParams()
  const id = Number(themeId)

  const { data: theme, isLoading, error } = useQuery({
    queryKey: ["themes", id],
    queryFn: () => fetchTheme(id),
  })

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto animate-pulse space-y-3">
        <div className="h-4 bg-muted rounded w-full" />
        <div className="h-4 bg-muted rounded w-3/4" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto text-center py-12">
        <p className="text-destructive">Failed to load theme.</p>
      </div>
    )
  }

  if (!theme) return null

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to feed
      </Link>
      <ThemeSection theme={theme} />
    </div>
  )
}
