import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import Markdown from "react-markdown"
import { fetchBreadcrumbs } from "@/lib/api"
import { useScrollReveal } from "@/hooks/use-scroll-reveal"
import { buildTree, type BreadcrumbNode } from "@/lib/tree"
import type { ThemePublic } from "@/lib/types"
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

  const tree = useMemo(
    () => (breadcrumbs ? buildTree(breadcrumbs) : []),
    [breadcrumbs],
  )

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

      {tree.length > 0 && (
        <div className="pl-4">
          {tree.map((node, i) => (
            <BreadcrumbTree key={node.id} node={node} depth={0} index={i} />
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
        <div className="flex justify-center py-2">
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
        <time
          dateTime={node.created_at}
          className="block text-[11px] text-muted-foreground/50 mt-1"
        >
          {formatRelativeTime(node.created_at)}
        </time>
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
