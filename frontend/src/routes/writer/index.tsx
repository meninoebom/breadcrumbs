import { createFileRoute } from "@tanstack/react-router"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchThemes, fetchAllDigests, generateDigest } from "@/lib/api"
import { ThemeCard } from "@/components/writer/theme-card"
import { DigestCard } from "@/components/writer/digest-card"
import type { DigestPublic, ThemePublic } from "@/lib/types"
import { dateKey } from "@/lib/utils"

export const Route = createFileRoute("/writer/")({
  component: WriterDashboard,
})

type FeedItem =
  | { kind: "theme"; key: string; date: string; theme: ThemePublic }
  | { kind: "digest"; key: string; date: string; digest: DigestPublic }

function buildWriterFeed(
  themes: ThemePublic[],
  digests: DigestPublic[],
): FeedItem[] {
  const items: FeedItem[] = []

  for (const theme of themes) {
    items.push({
      kind: "theme",
      key: `theme-${theme.id}`,
      date: dateKey(theme.created_at),
      theme,
    })
  }

  for (const digest of digests) {
    items.push({
      kind: "digest",
      key: `digest-${digest.id}`,
      date: digest.period_end,
      digest,
    })
  }

  items.sort((a, b) => b.date.localeCompare(a.date))
  return items
}

function WriterDashboard() {
  const qc = useQueryClient()

  const {
    data: themes,
    isLoading: themesLoading,
    error: themesError,
  } = useQuery({
    queryKey: ["themes", {}],
    queryFn: () => fetchThemes({}),
  })

  const {
    data: digests,
    isLoading: digestsLoading,
    error: digestsError,
  } = useQuery({
    queryKey: ["digests", "admin"],
    queryFn: fetchAllDigests,
  })

  const generate = useMutation({
    mutationFn: generateDigest,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["digests"] }),
  })

  if (themesLoading || digestsLoading) return <DashboardSkeleton />

  if (themesError || digestsError) {
    const msg = (themesError || digestsError)?.message ?? "Unknown error"
    return <p className="text-destructive">Error: {msg}</p>
  }

  const feed = buildWriterFeed(themes ?? [], digests ?? [])

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold tracking-tight">Dashboard</h2>
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

      {feed.length > 0 ? (
        <div className="grid gap-4">
          {feed.map((item) =>
            item.kind === "theme" ? (
              <ThemeCard key={item.key} theme={item.theme} />
            ) : (
              <DigestCard key={item.key} digest={item.digest} />
            ),
          )}
        </div>
      ) : (
        <p className="text-muted-foreground italic text-center py-8">
          Your notebook is empty. Start a new theme to begin leaving
          breadcrumbs.
        </p>
      )}
    </div>
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
