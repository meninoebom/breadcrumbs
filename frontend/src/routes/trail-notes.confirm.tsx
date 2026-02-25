import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"

export const Route = createFileRoute("/trail-notes/confirm")({
  component: ConfirmPage,
  validateSearch: (search: Record<string, unknown>) => ({
    token: typeof search.token === "string" ? search.token : "",
  }),
})

function ConfirmPage() {
  const { token } = Route.useSearch()

  const { data, isLoading, error } = useQuery({
    queryKey: ["confirm", token],
    queryFn: async () => {
      const res = await fetch(`/api/subscribers/confirm?token=${encodeURIComponent(token)}`)
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || "Confirmation failed")
      }
      return res.json() as Promise<{ message: string }>
    },
    enabled: !!token,
    retry: false,
  })

  return (
    <div className="max-w-md mx-auto py-16 text-center space-y-4">
      {isLoading && <p className="text-muted-foreground">Confirming...</p>}
      {error && (
        <p className="text-destructive">
          {error instanceof Error ? error.message : "Something went wrong"}
        </p>
      )}
      {data && (
        <>
          <h1 className="text-xl font-bold">You're on the path.</h1>
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
