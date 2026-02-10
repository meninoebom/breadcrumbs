import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { buttonVariants } from "@/components/ui/button"
import { fetchTags } from "@/lib/api"
import { cn } from "@/lib/utils"

interface TagBarProps {
  activeTag?: string
}

export function TagBar({ activeTag }: TagBarProps) {
  const { data: tags } = useQuery({
    queryKey: ["tags"],
    queryFn: fetchTags,
  })

  if (!tags || tags.length === 0) return null

  return (
    <div className="flex flex-wrap gap-1.5">
      <Link
        to="/"
        search={(prev) => ({ q: (prev as { q?: string }).q })}
        className={cn(
          buttonVariants({
            variant: activeTag ? "secondary" : "default",
            size: "sm",
          }),
          "no-underline",
        )}
      >
        All
      </Link>
      {tags.map((tag) => (
        <Link
          key={tag.id}
          to="/"
          search={(prev) => ({
            ...(prev as { q?: string }),
            tag: tag.name,
          })}
          className={cn(
            buttonVariants({
              variant: activeTag === tag.name ? "default" : "secondary",
              size: "sm",
            }),
            "no-underline",
          )}
        >
          {tag.name}
          <span className="ml-1 text-xs opacity-60">({tag.theme_count})</span>
        </Link>
      ))}
    </div>
  )
}
