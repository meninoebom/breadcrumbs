import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"

export const Route = createFileRoute("/digest/unsubscribe")({
  component: UnsubscribePage,
  validateSearch: (search: Record<string, unknown>) => ({
    token: typeof search.token === "string" ? search.token : "",
  }),
})

function UnsubscribePage() {
  const { token } = Route.useSearch()

  const { data, isLoading, error } = useQuery({
    queryKey: ["unsubscribe", token],
    queryFn: async () => {
      const res = await fetch(`/api/subscribers/unsubscribe?token=${encodeURIComponent(token)}`)
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || "Unsubscribe failed")
      }
      return res.json() as Promise<{ message: string }>
    },
    enabled: !!token,
    retry: false,
  })

  return (
    <div className="max-w-md mx-auto py-16 text-center space-y-4">
      {isLoading && <p className="text-muted-foreground">Processing...</p>}
      {error && (
        <p className="text-destructive">
          {error instanceof Error ? error.message : "Something went wrong"}
        </p>
      )}
      {data && (
        <>
          <h1 className="text-xl font-bold">Unsubscribed</h1>
          <p className="text-sm text-muted-foreground">{data.message}</p>
        </>
      )}
      <Link
        to="/"
        className="inline-block text-sm text-muted-foreground hover:text-foreground no-underline mt-4"
      >
        ← Back to crumb.blog
      </Link>
    </div>
  )
}
