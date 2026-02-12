import { useMemo } from "react"
import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { fetchTheme, fetchBreadcrumbs } from "@/lib/api"
import { buildTree } from "@/lib/tree"
import { ThemeHeaderEditor } from "@/components/writer/theme-header-editor"
import { BreadcrumbItem } from "@/components/writer/breadcrumb-item"
import { AddBreadcrumbForm } from "@/components/writer/add-breadcrumb-form"
import { Separator } from "@/components/ui/separator"

export const Route = createFileRoute("/writer/themes/$themeId")({
  component: ThemeEditor,
})

function ThemeEditor() {
  const { themeId } = Route.useParams()
  const id = Number(themeId)
  const isValidId = !Number.isNaN(id) && id > 0

  const {
    data: theme,
    isLoading: themeLoading,
    error: themeError,
  } = useQuery({
    queryKey: ["themes", id],
    queryFn: () => fetchTheme(id),
    enabled: isValidId,
  })

  const {
    data: breadcrumbs,
    isLoading: breadcrumbsLoading,
    error: breadcrumbsError,
  } = useQuery({
    queryKey: ["themes", id, "breadcrumbs"],
    queryFn: () => fetchBreadcrumbs(id),
    enabled: isValidId && !!theme,
  })

  const tree = useMemo(
    () => (breadcrumbs ? buildTree(breadcrumbs) : []),
    [breadcrumbs],
  )

  if (!isValidId) {
    return (
      <div className="py-12 text-center space-y-4">
        <p className="text-muted-foreground">Invalid theme ID.</p>
        <Link
          to="/writer"
          className="text-sm text-muted-foreground hover:text-foreground no-underline"
        >
          &larr; Back to dashboard
        </Link>
      </div>
    )
  }

  if (themeLoading) return <EditorSkeleton />

  if (themeError) {
    const is404 = themeError.message.includes("(404)")
    return (
      <div className="py-12 text-center space-y-4">
        <p className="text-muted-foreground">
          {is404 ? "Theme not found." : `Error: ${themeError.message}`}
        </p>
        <Link
          to="/writer"
          className="text-sm text-muted-foreground hover:text-foreground no-underline"
        >
          &larr; Back to dashboard
        </Link>
      </div>
    )
  }

  if (!theme) return null

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <ThemeHeaderEditor theme={theme} />

      <Separator />

      <div className="space-y-4">
        <h3 className="text-base font-semibold">
          Breadcrumbs
          {breadcrumbs && (
            <span className="text-muted-foreground font-normal">
              {" "}({breadcrumbs.length})
            </span>
          )}
        </h3>

        {breadcrumbsLoading && <BreadcrumbsSkeleton />}

        {breadcrumbsError && (
          <p className="text-sm text-destructive">
            Failed to load breadcrumbs: {breadcrumbsError.message}
          </p>
        )}

        {breadcrumbs && breadcrumbs.length === 0 && (
          <p className="text-sm text-muted-foreground italic py-4">
            This theme has no breadcrumbs yet. Drop your first thought.
          </p>
        )}

        {tree.length > 0 && (
          <div className="space-y-3">
            {tree.map((node) => (
              <BreadcrumbItem key={node.id} node={node} themeId={id} />
            ))}
          </div>
        )}

        <Separator />

        <AddBreadcrumbForm themeId={id} />
      </div>
    </div>
  )
}

function EditorSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="space-y-3">
        <div className="h-7 bg-muted rounded w-64" />
        <div className="h-4 bg-muted rounded w-48" />
      </div>
      <div className="h-px bg-border" />
      <div className="space-y-3">
        <div className="h-5 bg-muted rounded w-32" />
        <div className="h-16 bg-muted rounded w-full" />
        <div className="h-16 bg-muted rounded w-full" />
      </div>
    </div>
  )
}

function BreadcrumbsSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="rounded-lg border p-3 space-y-2">
        <div className="h-4 bg-muted rounded w-full" />
        <div className="h-3 bg-muted rounded w-24" />
      </div>
      <div className="rounded-lg border p-3 space-y-2">
        <div className="h-4 bg-muted rounded w-3/4" />
        <div className="h-3 bg-muted rounded w-24" />
      </div>
    </div>
  )
}
