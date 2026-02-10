import { useState } from "react"
import { createFileRoute, Link, Outlet } from "@tanstack/react-router"
import { Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { CreateThemeDialog } from "@/components/writer/create-theme-dialog"

export const Route = createFileRoute("/writer")({
  component: WriterLayout,
})

function WriterLayout() {
  const [dialogOpen, setDialogOpen] = useState(false)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            search={{}}
            className="text-sm text-muted-foreground hover:text-foreground no-underline"
          >
            &larr; Reader
          </Link>
          <h1 className="text-lg font-semibold">Writer</h1>
        </div>
        <Button size="sm" onClick={() => setDialogOpen(true)}>
          <Plus className="size-4" />
          New Theme
        </Button>
      </div>
      <Outlet />
      <CreateThemeDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </div>
  )
}
