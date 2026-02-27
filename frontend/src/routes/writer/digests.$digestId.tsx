import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import Markdown from "react-markdown"
import { fetchDigest, publishDigest, sendDigest } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { formatDate } from "@/lib/utils"

export const Route = createFileRoute("/writer/digests/$digestId")({
  component: DigestDetail,
})

const statusVariant: Record<string, "default" | "secondary" | "outline"> = {
  draft: "secondary",
  published: "default",
  sent: "outline",
}

function DigestDetail() {
  const { digestId } = Route.useParams()
  const id = Number(digestId)
  const isValidId = !Number.isNaN(id) && id > 0
  const qc = useQueryClient()

  const {
    data: digest,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["digests", id],
    queryFn: () => fetchDigest(id),
    enabled: isValidId,
  })

  const publish = useMutation({
    mutationFn: () => publishDigest(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["digests"] })
    },
  })

  const send = useMutation({
    mutationFn: () => sendDigest(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["digests"] })
    },
  })

  if (!isValidId) {
    return (
      <div className="py-12 text-center space-y-4">
        <p className="text-muted-foreground">Invalid digest ID.</p>
        <BackLink />
      </div>
    )
  }

  if (isLoading) return <DetailSkeleton />

  if (error) {
    const is404 = error.message.includes("(404)")
    return (
      <div className="py-12 text-center space-y-4">
        <p className="text-muted-foreground">
          {is404 ? "Digest not found." : `Error: ${error.message}`}
        </p>
        <BackLink />
      </div>
    )
  }

  if (!digest) return null

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <BackLink />

      <div className="space-y-2">
        <div className="flex items-start justify-between gap-2">
          <h1 className="text-xl font-semibold tracking-tight">
            {digest.title}
          </h1>
          <Badge variant={statusVariant[digest.status] ?? "secondary"}>
            {digest.status}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          {digest.period_start} – {digest.period_end}
          {" · "}Created {formatDate(digest.created_at)}
        </p>
      </div>

      <Separator />

      <div className="prose prose-sm max-w-none">
        <Markdown>{digest.summary_md}</Markdown>
      </div>

      <Separator />

      <div className="flex items-center gap-2">
        {digest.status === "draft" && (
          <button
            onClick={() => publish.mutate()}
            disabled={publish.isPending}
            className="text-sm px-4 py-2 rounded-md bg-foreground text-background hover:bg-foreground/90 disabled:opacity-50"
          >
            {publish.isPending ? "Publishing..." : "Publish"}
          </button>
        )}
        {digest.status === "published" && (
          <button
            onClick={() => {
              if (window.confirm("Send this digest to all subscribers?"))
                send.mutate()
            }}
            disabled={send.isPending}
            className="text-sm px-4 py-2 rounded-md bg-foreground text-background hover:bg-foreground/90 disabled:opacity-50"
          >
            {send.isPending ? "Sending..." : "Send to Subscribers"}
          </button>
        )}
      </div>
      {(publish.isError || send.isError) && (
        <p className="text-sm text-destructive">
          {(publish.error || send.error)?.message ??
            "An unexpected error occurred."}
        </p>
      )}
    </div>
  )
}

function BackLink() {
  return (
    <Link
      to="/writer"
      className="text-sm text-muted-foreground hover:text-foreground no-underline"
    >
      &larr; Back to dashboard
    </Link>
  )
}

function DetailSkeleton() {
  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-pulse">
      <div className="h-4 bg-muted rounded w-32" />
      <div className="space-y-2">
        <div className="h-7 bg-muted rounded w-64" />
        <div className="h-4 bg-muted rounded w-48" />
      </div>
      <div className="h-px bg-border" />
      <div className="space-y-2">
        <div className="h-4 bg-muted rounded w-full" />
        <div className="h-4 bg-muted rounded w-full" />
        <div className="h-4 bg-muted rounded w-3/4" />
      </div>
    </div>
  )
}
