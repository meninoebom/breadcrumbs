import { createRootRoute, Outlet } from "@tanstack/react-router"
import { TanStackRouterDevtools } from "@tanstack/router-devtools"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"

const queryClient = new QueryClient()

export const Route = createRootRoute({
  component: RootLayout,
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
      <TanStackRouterDevtools position="bottom-right" />
    </QueryClientProvider>
  )
}
