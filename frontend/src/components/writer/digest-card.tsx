import { Link } from "@tanstack/react-router"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { publishDigest, sendDigest } from "@/lib/api"
import type { DigestPublic } from "@/lib/types"
import { formatDate } from "@/lib/utils"
import { useMutation, useQueryClient } from "@tanstack/react-query"

const statusVariant: Record<string, "default" | "secondary" | "outline"> = {
  draft: "secondary",
  published: "default",
  sent: "outline",
}

export function DigestCard({ digest }: { digest: DigestPublic }) {
  const qc = useQueryClient()
  const invalidate = () => qc.invalidateQueries({ queryKey: ["digests"] })

  const publish = useMutation({
    mutationFn: () => publishDigest(digest.id),
    onSuccess: invalidate,
  })

  const send = useMutation({
    mutationFn: () => sendDigest(digest.id),
    onSuccess: invalidate,
  })

  return (
    <Link
      to="/writer/digests/$digestId"
      params={{ digestId: String(digest.id) }}
      className="no-underline"
    >
    <Card className="transition-colors hover:border-foreground/20">
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base">{digest.title}</CardTitle>
          <div className="flex gap-1.5">
            {digest.digest_type === "monthly" && (
              <Badge variant="outline">monthly</Badge>
            )}
            <Badge variant={statusVariant[digest.status] ?? "secondary"}>
              {digest.status}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground line-clamp-2">
          {digest.summary_md}
        </p>
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            {digest.period_start} – {digest.period_end}
            {" · "}Created {formatDate(digest.created_at)}
          </p>
          <div className="flex gap-2">
            {digest.status === "draft" && (
              <button
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); publish.mutate() }}
                disabled={publish.isPending}
                className="text-xs px-3 py-1 rounded-md bg-foreground text-background hover:bg-foreground/90 disabled:opacity-50"
              >
                {publish.isPending ? "..." : "Publish"}
              </button>
            )}
            {digest.status === "published" && (
              <button
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); if (window.confirm("Send this digest to all subscribers?")) send.mutate() }}
                disabled={send.isPending}
                className="text-xs px-3 py-1 rounded-md bg-foreground text-background hover:bg-foreground/90 disabled:opacity-50"
              >
                {send.isPending ? "..." : "Send"}
              </button>
            )}
          </div>
        </div>
        {(publish.isError || send.isError) && (
          <p className="text-xs text-destructive">
            {(publish.error || send.error)?.message ?? "An unexpected error occurred."}
          </p>
        )}
      </CardContent>
    </Card>
    </Link>
  )
}
