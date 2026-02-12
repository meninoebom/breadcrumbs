import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { fetchTags } from "@/lib/api"
import type { StreamSearch } from "@/lib/types"
import { cn } from "@/lib/utils"

interface TagBarProps {
  activeTag?: string
}

export function TagBar({ activeTag }: TagBarProps) {
  const { data: tags, error } = useQuery({
    queryKey: ["tags"],
    queryFn: fetchTags,
  })

  if (error) {
    console.error("Failed to load tags:", error.message)
    return null
  }

  if (!tags || tags.length === 0) return null

  return (
    <nav className="flex flex-wrap items-center gap-x-1 gap-y-1 text-sm text-muted-foreground">
      <Link
        to="/"
        search={(prev: StreamSearch) => ({ q: prev.q })}
        className={cn(
          "no-underline hover:text-foreground transition-colors",
          !activeTag ? "text-foreground font-medium underline underline-offset-4" : "",
        )}
      >
        all
      </Link>
      {tags.map((tag) => (
        <span key={tag.id} className="contents">
          <span className="text-muted-foreground/30 select-none">&middot;</span>
          <Link
            to="/"
            search={(prev: StreamSearch) => ({ q: prev.q, tag: tag.name })}
            className={cn(
              "no-underline hover:text-foreground transition-colors",
              activeTag === tag.name
                ? "text-foreground font-medium underline underline-offset-4"
                : "",
            )}
          >
            {tag.name}
          </Link>
        </span>
      ))}
    </nav>
  )
}
