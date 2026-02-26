import { createFileRoute } from "@tanstack/react-router"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchThemes, fetchAllDigests, generateDigest } from "@/lib/api"
import { ThemeCard } from "@/components/writer/theme-card"
import { DigestCard } from "@/components/writer/digest-card"

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

  return (
    <div className="max-w-3xl mx-auto space-y-10">
      {/* Themes */}
      <section className="grid gap-4">
        {themes && themes.length > 0 ? (
          themes.map((theme) => (
            <ThemeCard key={theme.id} theme={theme} />
          ))
        ) : (
          <p className="text-muted-foreground italic text-center py-8">
            Your notebook is empty. Start a new theme to begin leaving breadcrumbs.
          </p>
        )}
      </section>

      {/* Digests */}
      <DigestSection />
    </div>
  )
}

function DigestSection() {
  const qc = useQueryClient()
  const { data: digests, isLoading: digestsLoading, isError: digestsError, error: digestsErrorObj } = useQuery({
    queryKey: ["digests", "admin"],
    queryFn: fetchAllDigests,
  })

  const generate = useMutation({
    mutationFn: generateDigest,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["digests"] }),
  })

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold tracking-tight">Weekly Digests</h2>
        <button
          onClick={() => generate.mutate()}
          disabled={generate.isPending}
          className="text-sm px-3 py-1.5 rounded-md border hover:bg-muted disabled:opacity-50"
        >
          {generate.isPending ? "Generating..." : "Generate Digest"}
        </button>
      </div>
      {generate.isError && (
        <p className="text-xs text-destructive">{generate.error.message}</p>
      )}
      {digestsLoading && (
        <p className="text-sm text-muted-foreground">Loading digests...</p>
      )}
      {digestsError && (
        <p className="text-sm text-destructive">
          Failed to load digests: {digestsErrorObj?.message ?? "Unknown error"}
        </p>
      )}
      {!digestsLoading && !digestsError && digests && digests.length > 0 ? (
        <div className="grid gap-4">
          {digests.map((d) => (
            <DigestCard key={d.id} digest={d} />
          ))}
        </div>
      ) : !digestsLoading && !digestsError && (
        <p className="text-sm text-muted-foreground italic">No digests yet.</p>
      )}
    </section>
  )
}

function DashboardSkeleton() {
  return (
    <div className="max-w-3xl mx-auto grid gap-4">
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
