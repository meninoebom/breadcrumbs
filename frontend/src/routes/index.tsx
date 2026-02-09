import { createFileRoute } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"

interface Tag {
  id: number
  name: string
  theme_count: number
}

export const Route = createFileRoute("/")({
  component: HomePage,
})

function HomePage() {
  const { data: tags, isLoading, error } = useQuery<Tag[]>({
    queryKey: ["tags"],
    queryFn: async () => {
      const res = await fetch("/api/tags")
      if (!res.ok) throw new Error("Failed to fetch tags")
      return res.json()
    },
  })

  if (isLoading) {
    return <p className="text-muted-foreground">Loading tags...</p>
  }

  if (error) {
    return <p className="text-destructive">Error: {error.message}</p>
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-xl font-semibold">Tags</h2>
        <p className="text-sm text-muted-foreground">
          Full stack connected — fetching from the API.
        </p>
      </div>

      {tags && tags.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {tags.map((tag) => (
            <Button key={tag.id} variant="secondary" size="sm">
              {tag.name}
              <span className="ml-1.5 text-muted-foreground">
                {tag.theme_count}
              </span>
            </Button>
          ))}
        </div>
      ) : (
        <p className="text-muted-foreground">
          No tags yet. Start the backend and create some themes with tags.
        </p>
      )}
    </div>
  )
}
