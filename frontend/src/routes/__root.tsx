import React from "react"
import { createRootRoute, Outlet } from "@tanstack/react-router"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"

const TanStackRouterDevtools = import.meta.env.PROD
  ? () => null
  : React.lazy(() =>
      import("@tanstack/router-devtools").then((res) => ({
        default: res.TanStackRouterDevtools,
      })),
    )

const queryClient = new QueryClient()

export const Route = createRootRoute({
  component: RootLayout,
  errorComponent: ({ error }) => (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground p-8">
      <div className="max-w-md space-y-4">
        <h1 className="text-xl font-bold text-destructive">
          Something went wrong
        </h1>
        <pre className="text-sm bg-muted p-4 rounded overflow-auto">
          {error.message}
        </pre>
      </div>
    </div>
  ),
})

function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-background text-foreground">
        <header className="border-b px-6 py-4">
          <h1 className="text-2xl font-bold">Breadcrumbs</h1>
        </header>
        <main className="mx-auto max-w-3xl px-6 py-8">
          <Outlet />
        </main>
      </div>
      <React.Suspense>
        <TanStackRouterDevtools position="bottom-right" />
      </React.Suspense>
    </QueryClientProvider>
  )
}
