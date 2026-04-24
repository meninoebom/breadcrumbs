import type { DigestPublic, ThemePublic } from "@/lib/types"
import { dateKey } from "@/lib/utils"

export type FeedItem =
  | { kind: "date-group"; key: string; date: string; themes: ThemePublic[] }
  | { kind: "weekly-summary"; key: string; date: string; digest: DigestPublic }

/**
 * Merge date-grouped themes and weekly digests into a single
 * chronologically-sorted feed (newest first).
 *
 * `excludeWeeklyInMonths` suppresses weekly digests whose period_end falls
 * in a listed YYYY-MM — used by the home feed to hide weekly summaries for
 * months that render as collapsed cards (those surface on expand).
 */
export function buildFeed(
  themes: ThemePublic[],
  digests: DigestPublic[],
  excludeWeeklyInMonths?: Set<string>,
): FeedItem[] {
  const groups = new Map<string, ThemePublic[]>()
  for (const theme of themes) {
    const key = dateKey(theme.created_at)
    const list = groups.get(key)
    if (list) list.push(theme)
    else groups.set(key, [theme])
  }

  const items: FeedItem[] = []
  for (const [key, groupThemes] of groups) {
    items.push({ kind: "date-group", key, date: key, themes: groupThemes })
  }
  for (const digest of digests) {
    if (digest.digest_type !== "weekly") continue
    if (excludeWeeklyInMonths?.has(digest.period_end.slice(0, 7))) continue
    items.push({
      kind: "weekly-summary",
      key: `summary-${digest.id}`,
      date: digest.period_end,
      digest,
    })
  }
  items.sort((a, b) => b.date.localeCompare(a.date))
  return items
}
