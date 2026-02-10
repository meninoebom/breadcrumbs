import { createFileRoute } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { fetchThemes } from "@/lib/api"
import { ThemeCard } from "@/components/writer/theme-card"

export const Route = createFileRoute("/writer/")({
  component: WriterDashboard,
})

function WriterDashboard() {
  const { data: themes, isLoading, error } = useQuery({
    queryKey: ["themes", {}],
    queryFn: () => fetchThemes({}),
  })

  if (isLoading) return <DashboardSkeleton />

  if (error) {
    return <p className="text-destructive">Error: {error.message}</p>
  }

  if (!themes || themes.length === 0) {
    return (
      <div className="py-12 text-center space-y-2">
        <p className="text-muted-foreground">No themes yet.</p>
        <p className="text-sm text-muted-foreground">
          Create your first theme to get started.
        </p>
      </div>
    )
  }

  return (
    <div className="grid gap-4">
      {themes.map((theme) => (
        <ThemeCard key={theme.id} theme={theme} />
      ))}
    </div>
  )
}

function DashboardSkeleton() {
  return (
    <div className="grid gap-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="rounded-xl border p-6 space-y-3 animate-pulse">
          <div className="flex justify-between">
            <div className="h-5 bg-muted rounded w-48" />
            <div className="h-5 bg-muted rounded w-16" />
          </div>
          <div className="h-3 bg-muted rounded w-32" />
        </div>
      ))}
    </div>
  )
}
