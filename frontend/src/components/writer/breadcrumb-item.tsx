import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Pencil, Trash2, Check, X } from "lucide-react"
import Markdown from "react-markdown"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { updateBreadcrumb, deleteBreadcrumb } from "@/lib/api"
import type { BreadcrumbPublic } from "@/lib/types"
import { formatDate } from "@/lib/utils"

interface BreadcrumbItemProps {
  breadcrumb: BreadcrumbPublic
  themeId: number
}

export function BreadcrumbItem({ breadcrumb, themeId }: BreadcrumbItemProps) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [bodyMd, setBodyMd] = useState(breadcrumb.body_md)

  const editMutation = useMutation({
    mutationFn: (data: { body_md: string }) =>
      updateBreadcrumb(themeId, breadcrumb.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["themes", themeId, "breadcrumbs"],
      })
      setEditing(false)
    },
  })

  const removeMutation = useMutation({
    mutationFn: () => deleteBreadcrumb(themeId, breadcrumb.id),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["themes", themeId, "breadcrumbs"],
      })
    },
  })

  function handleSave() {
    if (!bodyMd.trim()) return
    editMutation.mutate({ body_md: bodyMd.trim() })
  }

  function handleCancel() {
    setBodyMd(breadcrumb.body_md)
    setEditing(false)
  }

  if (editing) {
    return (
      <div className="rounded-lg border p-3 space-y-3">
        <Textarea
          value={bodyMd}
          onChange={(e) => setBodyMd(e.target.value)}
          rows={4}
          autoFocus
        />
        {editMutation.error && (
          <p className="text-sm text-destructive">
            {editMutation.error.message}
          </p>
        )}
        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={handleSave}
            disabled={editMutation.isPending || !bodyMd.trim()}
          >
            <Check className="size-4" />
            {editMutation.isPending ? "Saving..." : "Save"}
          </Button>
          <Button size="sm" variant="outline" onClick={handleCancel}>
            <X className="size-4" />
            Cancel
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="group rounded-lg border p-3 space-y-1">
      <div className="flex items-start justify-between gap-2">
        <div className="prose prose-sm max-w-none flex-1">
          <Markdown>{breadcrumb.body_md}</Markdown>
        </div>
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          <Button
            size="icon-xs"
            variant="ghost"
            onClick={() => setEditing(true)}
          >
            <Pencil className="size-3.5" />
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                size="icon-xs"
                variant="ghost"
                disabled={removeMutation.isPending}
              >
                <Trash2 className="size-3.5" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete breadcrumb?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will permanently delete this breadcrumb. This action
                  cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={() => removeMutation.mutate()}>
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>
      <time className="block text-xs text-muted-foreground">
        {formatDate(breadcrumb.created_at)}
        {breadcrumb.updated_at && <> &middot; edited</>}
      </time>
      {removeMutation.error && (
        <p className="text-sm text-destructive">
          {removeMutation.error.message}
        </p>
      )}
    </div>
  )
}
