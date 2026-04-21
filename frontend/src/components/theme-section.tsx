import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import Markdown from "react-markdown"
import { LinkIcon } from "lucide-react"
import { fetchBreadcrumbs } from "@/lib/api"
import { useScrollReveal } from "@/hooks/use-scroll-reveal"
import { buildTree, type BreadcrumbNode } from "@/lib/tree"
import type { ThemePublic } from "@/lib/types"
import { cn } from "@/lib/utils"

interface ThemeSectionProps {
  theme: ThemePublic
  variant?: "feed" | "permalink"
}

export function ThemeSection({ theme, variant = "feed" }: ThemeSectionProps) {
  const {
    data: breadcrumbs,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["themes", theme.id, "breadcrumbs"],
    queryFn: () => fetchBreadcrumbs(theme.id),
  })

  const tree = useMemo(
    () => (breadcrumbs ? buildTree(breadcrumbs) : []),
    [breadcrumbs],
  )

  return (
    <article id={`theme-${theme.id}`} className="group/theme space-y-3">
      {theme.image_url && variant === "permalink" && (
        <img
          src={theme.image_url}
          alt=""
          className="w-60 h-60 rounded object-cover"
        />
      )}
      <div className="flex items-start gap-3">
        {theme.image_url && variant === "feed" && (
          <img
            src={theme.image_url}
            alt=""
            className="w-14 h-14 rounded object-cover flex-shrink-0 mt-0.5"
          />
        )}
        <div className="prose prose-sm max-w-none flex-1">
          <Markdown>{theme.body_md}</Markdown>
        </div>
        <Link
          to="/themes/$themeId"
          params={{ themeId: String(theme.id) }}
          className="mt-1 opacity-0 group-hover/theme:opacity-100 transition-opacity text-muted-foreground/40 hover:text-muted-foreground"
          title="Permalink"
        >
          <LinkIcon className="h-3.5 w-3.5" />
        </Link>
      </div>

      {isLoading && <BreadcrumbSkeleton />}

      {error && (
        <p className="text-sm text-destructive">
          Failed to load breadcrumbs: {error.message}
        </p>
      )}

      {tree.length > 0 && (
        <div className="pl-4">
          {tree.map((node, i) => (
            <BreadcrumbTree key={node.id} node={node} depth={0} index={i} />
          ))}
        </div>
      )}

      {theme.tags.length > 0 && (
        <div className="flex flex-wrap gap-x-1 gap-y-1 pt-1">
          {theme.tags.map((tag) => (
            <Link
              key={tag.id}
              to="/"
              search={{ tag: tag.name }}
              className="text-xs text-muted-foreground/70 hover:text-foreground no-underline transition-colors py-1 px-1.5"
            >
              #{tag.name}
            </Link>
          ))}
        </div>
      )}
    </article>
  )
}

const INDENT_PX = [0, 16, 32, 48] as const

function BreadcrumbTree({
  node,
  depth,
  index,
}: {
  node: BreadcrumbNode
  depth: number
  index: number
}) {
  const { ref, revealed } = useScrollReveal<HTMLDivElement>()
  const indent = INDENT_PX[Math.min(depth, 3)]

  return (
    <div ref={ref} style={indent > 0 ? { marginLeft: indent } : undefined}>
      {depth === 0 && index > 0 && (
        <div className="flex justify-center py-0.5">
          <span className="text-muted-foreground/30 text-xs">·</span>
        </div>
      )}
      <div
        className={cn("opacity-0", revealed && "animate-fade-up")}
        style={revealed ? { animationDelay: `${index * 50}ms` } : undefined}
      >
        <div className="prose prose-sm max-w-none">
          <Markdown>{node.body_md}</Markdown>
        </div>
      </div>
      {node.children.map((child, i) => (
        <BreadcrumbTree key={child.id} node={child} depth={depth + 1} index={i} />
      ))}
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
