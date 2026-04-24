import { useMemo } from "react"
import { useNavigate } from "@tanstack/react-router"
import type { DigestPublic } from "@/lib/types"

function formatMonthLabel(periodStart: string): string {
  const d = new Date(periodStart + "T00:00:00")
  if (isNaN(d.getTime())) return periodStart
  return new Intl.DateTimeFormat("en-US", { month: "short", year: "numeric" }).format(d)
}

export function DigestNav({ digests }: { digests: DigestPublic[] }) {
  const navigate = useNavigate()
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
        Monthly Digests
      </h3>
      <nav className="flex flex-col gap-1">
        {monthly.map((digest) => {
          const monthKey = digest.period_start.slice(0, 7) // YYYY-MM
          return (
            <a
              key={digest.id}
              href={`#month-${monthKey}`}
              onClick={(e) => {
                e.preventDefault()
                // Clear any tag/q filter and ensure this month is open, then
                // scroll after the card renders.
                navigate({
                  to: "/",
                  search: { open: monthKey },
                }).then(() => {
                  requestAnimationFrame(() => {
                    const target =
                      document.getElementById(`month-${monthKey}`) ??
                      document.getElementById(`digest-${digest.id}`)
                    target?.scrollIntoView({ behavior: "smooth" })
                  })
                })
              }}
              className="text-sm text-muted-foreground/70 hover:text-foreground transition-colors"
            >
              {formatMonthLabel(digest.period_start)}
            </a>
          )
        })}
      </nav>
    </div>
  )
}
