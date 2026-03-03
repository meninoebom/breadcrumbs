import { useMemo } from "react"
import type { DigestPublic } from "@/lib/types"

function formatMonthLabel(periodStart: string): string {
  const d = new Date(periodStart + "T00:00:00")
  if (isNaN(d.getTime())) return periodStart
  return new Intl.DateTimeFormat("en-US", { month: "short", year: "numeric" }).format(d)
}

export function DigestNav({ digests }: { digests: DigestPublic[] }) {
  const monthly = useMemo(
    () =>
      digests
        .filter((d) => d.digest_type === "monthly")
        .sort((a, b) => b.period_start.localeCompare(a.period_start)),
    [digests],
  )

  if (monthly.length === 0) return null

  return (
    <div>
      <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground/60 mb-3">
        Digests
      </h3>
      <nav className="flex flex-col gap-1">
        {monthly.map((digest) => (
          <a
            key={digest.id}
            href={`#digest-${digest.id}`}
            onClick={(e) => {
              const target = document.getElementById(`digest-${digest.id}`)
              if (target) {
                e.preventDefault()
                target.scrollIntoView({ behavior: "smooth" })
              }
            }}
            className="text-sm text-muted-foreground/70 hover:text-foreground transition-colors"
          >
            {formatMonthLabel(digest.period_start)}
          </a>
        ))}
      </nav>
    </div>
  )
}
