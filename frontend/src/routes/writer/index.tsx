import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchThemes, fetchAllDigests, generateDigest } from "@/lib/api"
import { ThemeCard } from "@/components/writer/theme-card"
import { DigestCard } from "@/components/writer/digest-card"
import type { DigestPublic, DigestType, ThemePublic } from "@/lib/types"
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

  const [digestType, setDigestType] = useState<DigestType>("weekly")
  const generate = useMutation({
    mutationFn: (type: DigestType) => generateDigest(type),
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
        <div className="flex items-center gap-1.5">
          <select
            value={digestType}
            onChange={(e) => setDigestType(e.target.value as DigestType)}
            className="text-xs text-muted-foreground bg-transparent border rounded px-1.5 py-1"
          >
            <option value="weekly">weekly</option>
            <option value="monthly">monthly</option>
          </select>
          <button
            onClick={() => generate.mutate(digestType)}
            disabled={generate.isPending}
            className="text-xs text-muted-foreground hover:text-foreground disabled:opacity-50"
          >
            {generate.isPending ? "Generating..." : "Generate Digest"}
          </button>
        </div>
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
