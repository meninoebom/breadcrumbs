import type { DigestPublic } from "@/lib/types"
import { Sparkles } from "lucide-react"

function formatWeekRange(start: string, end: string): string {
  const s = new Date(start + "T00:00:00")
  const e = new Date(end + "T00:00:00")
  const startFmt = new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric" }).format(s)
  const endFmt = new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric", year: "numeric" }).format(e)
  return `Week of ${startFmt}–${endFmt}`
}

function formatMonthRange(start: string): string {
  const s = new Date(start + "T00:00:00")
  return new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric" }).format(s)
}

function formatDigestHeading(digest: DigestPublic): string {
  if (digest.digest_type === "monthly") {
    return formatMonthRange(digest.period_start)
  }
  return formatWeekRange(digest.period_start, digest.period_end)
}

export function WeeklySummary({ digest }: { digest: DigestPublic }) {
  return (
    <section>
      <h2 className="text-lg font-semibold tracking-tight mb-4 text-muted-foreground/70">
        {formatDigestHeading(digest)}
      </h2>
      <div className="relative rounded-lg border border-dashed border-border/60 bg-muted/20 px-5 py-4">
        <p className="text-sm leading-relaxed text-muted-foreground">
          {digest.summary_md}
        </p>
        <span title="AI-generated summary">
          <Sparkles className="absolute bottom-2 right-3 h-3 w-3 text-muted-foreground/25" />
        </span>
      </div>
    </section>
  )
}
