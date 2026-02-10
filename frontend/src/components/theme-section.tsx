import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import Markdown from "react-markdown"
import { buttonVariants } from "@/components/ui/button"
import { fetchBreadcrumbs } from "@/lib/api"
import type { ThemePublic } from "@/lib/types"
import { cn, formatDate } from "@/lib/utils"

export function ThemeSection({ theme }: { theme: ThemePublic }) {
  const {
    data: breadcrumbs,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["themes", theme.id, "breadcrumbs"],
    queryFn: () => fetchBreadcrumbs(theme.id),
  })

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold tracking-tight">{theme.title}</h2>

      {theme.description_md && (
        <div className="prose prose-sm text-muted-foreground">
          <Markdown>{theme.description_md}</Markdown>
        </div>
      )}

      {theme.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {theme.tags.map((tag) => (
            <Link
              key={tag.id}
              to="/"
              search={{ tag: tag.name }}
              className={cn(
                buttonVariants({ variant: "secondary", size: "sm" }),
                "no-underline",
              )}
            >
              {tag.name}
            </Link>
          ))}
        </div>
      )}

      {isLoading && <BreadcrumbSkeleton />}

      {error && (
        <p className="text-sm text-destructive">Failed to load breadcrumbs</p>
      )}

      {breadcrumbs && breadcrumbs.length > 0 && (
        <div className="space-y-4 pt-2">
          {breadcrumbs.map((bc) => (
            <div key={bc.id} className="space-y-1">
              <time className="block text-xs text-muted-foreground">
                {formatDate(bc.created_at)}
              </time>
              <div className="prose prose-sm max-w-none">
                <Markdown>{bc.body_md}</Markdown>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function BreadcrumbSkeleton() {
  return (
    <div className="space-y-3 animate-pulse pt-2">
      <div className="h-3 bg-muted rounded w-24" />
      <div className="h-4 bg-muted rounded w-full" />
      <div className="h-4 bg-muted rounded w-3/4" />
      <div className="h-3 bg-muted rounded w-24 mt-4" />
      <div className="h-4 bg-muted rounded w-5/6" />
    </div>
  )
}
