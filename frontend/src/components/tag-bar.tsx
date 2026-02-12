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
    <nav className="space-y-1 text-sm">
      <Link
        to="/"
        search={(prev: StreamSearch) => ({ q: prev.q })}
        className={cn(
          "block no-underline hover:text-foreground transition-colors",
          !activeTag
            ? "text-foreground font-medium"
            : "text-muted-foreground",
        )}
      >
        all
      </Link>
      {tags.map((tag) => (
        <Link
          key={tag.id}
          to="/"
          search={(prev: StreamSearch) => ({ q: prev.q, tag: tag.name })}
          className={cn(
            "block no-underline hover:text-foreground transition-colors",
            activeTag === tag.name
              ? "text-foreground font-medium"
              : "text-muted-foreground",
          )}
        >
          {tag.name}
        </Link>
      ))}
    </nav>
  )
}
