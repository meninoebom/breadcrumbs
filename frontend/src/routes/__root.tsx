import React from "react"
import {
  createRootRoute,
  Link,
  Outlet,
  useNavigate,
  useRouterState,
} from "@tanstack/react-router"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Search, PenLine } from "lucide-react"
import type { StreamSearch } from "@/lib/types"

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

function SearchBar() {
  const navigate = useNavigate()
  const currentQ = useRouterState({
    select: (s) => {
      const search = s.location.search as Record<string, unknown>
      return typeof search?.q === "string" ? search.q : ""
    },
  })

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const raw = new FormData(e.currentTarget).get("q")
    const q = typeof raw === "string" ? raw.trim() : ""
    navigate({
      to: "/",
      search: (prev: StreamSearch) => ({
        tag: prev.tag,
        q: q || undefined,
      }),
    })
  }

  return (
    <form onSubmit={handleSubmit} className="relative">
      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
      <input
        key={currentQ}
        name="q"
        type="text"
        defaultValue={currentQ}
        placeholder="Search..."
        className="h-8 w-48 rounded-md border bg-background pl-8 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
      />
    </form>
  )
}

function RootLayout() {
  const isWriterRoute = useRouterState({
    select: (s) => s.location.pathname.startsWith("/writer"),
  })

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-background text-foreground">
        <header className="border-b px-6 py-4">
          <div className="mx-auto max-w-5xl flex items-center justify-between">
            <div>
              <Link
                to="/"
                search={{}}
                className="text-2xl font-bold no-underline text-foreground"
              >
                Breadcrumbs
              </Link>
              <p className="text-sm italic text-muted-foreground">
                small thoughts, dropped along the way
              </p>
            </div>
            <div className="flex items-center gap-3">
              {!isWriterRoute && <SearchBar />}
              <Link
                to="/about"
                className="text-sm text-muted-foreground hover:text-foreground no-underline"
              >
                About
              </Link>
              <Link
                to="/writer"
                className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground no-underline"
              >
                <PenLine className="size-4" />
                Write
              </Link>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-6 py-8">
          <Outlet />
        </main>
      </div>
      <React.Suspense>
        <TanStackRouterDevtools position="bottom-right" />
      </React.Suspense>
    </QueryClientProvider>
  )
}
