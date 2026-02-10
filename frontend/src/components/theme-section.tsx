import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import Markdown from "react-markdown"
import { fetchBreadcrumbs } from "@/lib/api"
import type { ThemePublic } from "@/lib/types"

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
        <div className="space-y-2 pl-4">
          {breadcrumbs.map((bc) => (
            <div key={bc.id} className="prose prose-sm max-w-none">
              <Markdown>{bc.body_md}</Markdown>
            </div>
          ))}
        </div>
      )}

      {theme.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {theme.tags.map((tag) => (
            <Link
              key={tag.id}
              to="/"
              search={{ tag: tag.name }}
              className="text-xs text-muted-foreground hover:text-foreground no-underline"
            >
              {tag.name}
            </Link>
          ))}
        </div>
      )}
    </article>
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
