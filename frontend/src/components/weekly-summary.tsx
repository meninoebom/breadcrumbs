import type { DigestPublic } from "@/lib/types"

function formatWeekRange(start: string, end: string): string {
  const s = new Date(start + "T00:00:00")
  const e = new Date(end + "T00:00:00")
  const startFmt = new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric" }).format(s)
  const endFmt = new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric", year: "numeric" }).format(e)
  return `Week of ${startFmt}–${endFmt}`
}

export function WeeklySummary({ digest }: { digest: DigestPublic }) {
  return (
    <section>
      <h2 className="text-lg font-semibold tracking-tight mb-4 text-muted-foreground/70">
        {formatWeekRange(digest.period_start, digest.period_end)}
      </h2>
      <div className="rounded-lg border border-dashed border-border/60 bg-muted/20 px-5 py-4">
        <p className="text-sm leading-relaxed text-muted-foreground">
          {digest.summary_md}
        </p>
      </div>
    </section>
  )
}
