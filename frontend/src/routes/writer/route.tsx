import { useState } from "react"
import { createFileRoute, Link, Outlet, redirect } from "@tanstack/react-router"
import { Plus } from "lucide-react"
import { isAuthenticated } from "@/lib/auth"
import { Button } from "@/components/ui/button"
import { CreateThemeDialog } from "@/components/writer/create-theme-dialog"

export const Route = createFileRoute("/writer")({
  beforeLoad: () => {
    if (!isAuthenticated()) {
      throw redirect({ to: "/login" })
    }
  },
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
          <Link
            to="/writer"
            className="text-lg font-semibold no-underline text-foreground"
          >
            Writer
          </Link>
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
