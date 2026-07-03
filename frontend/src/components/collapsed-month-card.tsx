import { useQuery } from "@tanstack/react-query"
import { ChevronDown, Sparkles } from "lucide-react"
import Markdown from "react-markdown"
import { ThemeSection } from "@/components/theme-section"
import { WeeklySummary } from "@/components/weekly-summary"
import { fetchThemes } from "@/lib/api"
import { buildFeed } from "@/lib/feed"
import type { DigestPublic, MonthSummary } from "@/lib/types"
import { cn, formatDateHeading } from "@/lib/utils"

interface Props {
  month: MonthSummary
  digests: DigestPublic[]
  isOpen: boolean
  onToggle: () => void
}

function formatMonthHeading(year: number, month: number): string {
  // Local-time constructor — matches the formatter's local timezone so we
  // don't get "January 2026" displayed for a February card in UTC-offset zones.
  return new Intl.DateTimeFormat("en-US", {
    month: "long",
    year: "numeric",
  }).format(new Date(year, month - 1, 1))
}

function monthParam(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, "0")}`
}

export function CollapsedMonthCard({ month, digests, isOpen, onToggle }: Props) {
  const param = monthParam(month.year, month.month)
  const heading = formatMonthHeading(month.year, month.month)

  const { data: themes, isLoading } = useQuery({
    queryKey: ["themes", { month: param, visibility: "published" }],
    queryFn: () => fetchThemes({ visibility: "published", month: param }),
    enabled: isOpen,
  })

  const weeklyDigests = digests.filter(
    (d) => d.digest_type === "weekly" && d.period_start.startsWith(param),
  )

  const entries = isOpen ? buildFeed(themes ?? [], weeklyDigests) : []
  const themeWord = month.theme_count === 1 ? "theme" : "themes"

  return (
    <section id={`month-${param}`}>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isOpen}
        className="group flex w-full items-start gap-3 py-2 text-left transition-colors"
      >
        <ChevronDown
          className={cn(
            "mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-transform",
            isOpen ? "rotate-0" : "-rotate-90",
          )}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="text-lg font-semibold tracking-tight">{heading}</h2>
            <span className="text-xs text-muted-foreground shrink-0">
              {month.theme_count} {themeWord}
            </span>
          </div>
          {!isOpen && month.monthly_digest && (
            <div className="mt-2 line-clamp-3">
              <div className="prose prose-sm max-w-none text-sm leading-relaxed text-muted-foreground">
                <Markdown>{month.monthly_digest.summary_md}</Markdown>
              </div>
            </div>
          )}
        </div>
      </button>

      {isOpen && (
        <div className="mt-4 space-y-8">
          {month.monthly_digest && (
            <div className="relative rounded-md border border-dashed border-border/60 bg-muted/20 px-4 py-3">
              <div className="prose prose-sm max-w-none text-sm leading-relaxed text-muted-foreground">
                <Markdown>{month.monthly_digest.summary_md}</Markdown>
              </div>
              <span title="AI-generated summary">
                <Sparkles className="absolute bottom-2 right-3 h-3 w-3 text-muted-foreground/25" />
              </span>
            </div>
          )}

          {isLoading && (
            <p className="text-sm text-muted-foreground italic">Loading…</p>
          )}

          {entries.map((item) =>
            item.kind === "date-group" ? (
              <section key={item.key}>
                <h3 className="text-base font-semibold tracking-tight mb-4">
                  {formatDateHeading(item.themes[0].created_at)}
                </h3>
                <div className="space-y-8 pl-4 border-l-2 border-border">
                  {item.themes.map((theme) => (
                    <ThemeSection key={theme.id} theme={theme} />
                  ))}
                </div>
              </section>
            ) : (
              <WeeklySummary key={item.key} digest={item.digest} />
            ),
          )}
        </div>
      )}
    </section>
  )
}
