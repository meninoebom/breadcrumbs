import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import Markdown from "react-markdown"
import { fetchBreadcrumbs } from "@/lib/api"
import { useScrollReveal } from "@/hooks/use-scroll-reveal"
import type { BreadcrumbPublic, ThemePublic } from "@/lib/types"
import { cn, formatRelativeTime } from "@/lib/utils"

interface ThemeSectionProps {
  theme: ThemePublic
}

export function ThemeSection({ theme }: ThemeSectionProps) {
  const {
    data: breadcrumbs,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["themes", theme.id, "breadcrumbs"],
    queryFn: () => fetchBreadcrumbs(theme.id),
  })

  return (
    <article className="space-y-3">
      <div className="prose prose-sm max-w-none">
        <Markdown>{theme.body_md}</Markdown>
      </div>

      {isLoading && <BreadcrumbSkeleton />}

      {error && (
        <p className="text-sm text-destructive">
          Failed to load breadcrumbs: {error.message}
        </p>
      )}

      {breadcrumbs && breadcrumbs.length > 0 && (
        <div className="pl-4">
          {breadcrumbs.map((bc, i) => (
            <BreadcrumbEntry key={bc.id} bc={bc} showSeparator={i > 0} delay={i * 50} />
          ))}
        </div>
      )}

      {theme.tags.length > 0 && (
        <div className="flex flex-wrap gap-x-2 gap-y-1 pt-1">
          {theme.tags.map((tag) => (
            <Link
              key={tag.id}
              to="/"
              search={{ tag: tag.name }}
              className="text-xs text-muted-foreground/70 hover:text-foreground no-underline transition-colors"
            >
              #{tag.name}
            </Link>
          ))}
        </div>
      )}
    </article>
  )
}

function BreadcrumbEntry({
  bc,
  showSeparator,
  delay,
}: {
  bc: BreadcrumbPublic
  showSeparator: boolean
  delay: number
}) {
  const { ref, revealed } = useScrollReveal<HTMLDivElement>()

  return (
    <div ref={ref}>
      {showSeparator && (
        <div className="flex justify-center py-2">
          <span className="text-muted-foreground/30 text-xs">·</span>
        </div>
      )}
      <div
        className={cn("opacity-0", revealed && "animate-fade-up")}
        style={revealed ? { animationDelay: `${delay}ms` } : undefined}
      >
        <div className="prose prose-sm max-w-none">
          <Markdown>{bc.body_md}</Markdown>
        </div>
        <time
          dateTime={bc.created_at}
          className="block text-[11px] text-muted-foreground/50 mt-1"
        >
          {formatRelativeTime(bc.created_at)}
        </time>
      </div>
    </div>
  )
}

function BreadcrumbSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-4 bg-muted rounded w-full" />
      <div className="h-4 bg-muted rounded w-3/4" />
      <div className="h-4 bg-muted rounded w-5/6" />
    </div>
  )
}
