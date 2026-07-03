import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { Link2 } from "lucide-react"
import Markdown from "react-markdown"
import { fetchBreadcrumbs } from "@/lib/api"
import { useScrollReveal } from "@/hooks/use-scroll-reveal"
import { buildTree, type BreadcrumbNode } from "@/lib/tree"
import type { ThemePublic } from "@/lib/types"
import { cn } from "@/lib/utils"

interface ThemeSectionProps {
  theme: ThemePublic
  variant?: "feed" | "permalink"
  animate?: boolean
}

export function ThemeSection({ theme, variant = "feed", animate = true }: ThemeSectionProps) {
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

  const isFeed = variant === "feed"

  return (
    <article id={`theme-${theme.id}`} className="group space-y-3">
      <div className="relative">
        {isFeed && (
          <Link
            to="/themes/$themeId"
            params={{ themeId: String(theme.id) }}
            aria-label="Theme permalink"
            className="absolute top-0 right-0 z-10 p-1 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity"
          >
            <Link2 className="size-3.5 text-muted-foreground/50 hover:text-foreground" />
          </Link>
        )}
        {theme.image_url && (
          <img
            src={theme.image_url}
            alt=""
            className={cn(
              "w-full rounded-lg object-cover",
              variant === "permalink" ? "aspect-[5/2]" : "aspect-[3/1]",
            )}
          />
        )}
        <div
          className={cn(
            "prose prose-sm max-w-none",
            theme.image_url && "mt-3",
          )}
        >
          <Markdown>{theme.body_md}</Markdown>
        </div>
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
            <BreadcrumbTree key={node.id} node={node} depth={0} index={i} animate={animate} />
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
  animate,
}: {
  node: BreadcrumbNode
  depth: number
  index: number
  animate: boolean
}) {
  const { ref, revealed } = useScrollReveal<HTMLDivElement>()
  const indent = INDENT_PX[Math.min(depth, 3)]
  const isRevealed = !animate || revealed

  return (
    <div ref={animate ? ref : undefined} style={indent > 0 ? { marginLeft: indent } : undefined}>
      {depth === 0 && index > 0 && (
        <div className="flex justify-center py-0.5">
          <span className="text-muted-foreground/30 text-xs">·</span>
        </div>
      )}
      <div
        className={cn(!isRevealed && "opacity-0", animate && revealed && "animate-fade-up")}
        style={animate && revealed ? { animationDelay: `${index * 50}ms` } : undefined}
      >
        <div className="prose prose-sm max-w-none">
          <Markdown>{node.body_md}</Markdown>
        </div>
      </div>
      {node.children.map((child, i) => (
        <BreadcrumbTree key={child.id} node={child} depth={depth + 1} index={i} animate={animate} />
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
