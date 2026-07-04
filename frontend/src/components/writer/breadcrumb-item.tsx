import { useEffect, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Pencil, Trash2, Check, X, MessageSquare } from "lucide-react"
import Markdown from "react-markdown"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  MarkdownPreview,
  WritePreviewToggle,
  type WritePreviewMode,
} from "./markdown-field"
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
import { AddBreadcrumbForm } from "./add-breadcrumb-form"
import { useHighlight } from "./highlight-context"
import type { BreadcrumbNode } from "@/lib/tree"
import { cn, formatDate } from "@/lib/utils"

const INDENT_PX = [0, 16, 32, 48] as const

interface BreadcrumbItemProps {
  node: BreadcrumbNode
  themeId: number
  depth?: number
}

export function BreadcrumbItem({ node, themeId, depth = 0 }: BreadcrumbItemProps) {
  const queryClient = useQueryClient()
  const { highlightedId } = useHighlight()
  const [editing, setEditing] = useState(false)
  const [editMode, setEditMode] = useState<WritePreviewMode>("write")
  const [replying, setReplying] = useState(false)
  const [bodyMd, setBodyMd] = useState(node.body_md)
  const isHighlighted = highlightedId === node.id

  // Sync local state when prop changes (e.g. after mutation + refetch)
  useEffect(() => {
    if (!editing) {
      setBodyMd(node.body_md)
    }
  }, [node.body_md, editing])

  const editMutation = useMutation({
    mutationFn: (data: { body_md: string }) =>
      updateBreadcrumb(themeId, node.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["themes", themeId, "breadcrumbs"],
      })
      setEditing(false)
    },
  })

  const removeMutation = useMutation({
    mutationFn: () => deleteBreadcrumb(themeId, node.id),
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
    setBodyMd(node.body_md)
    setEditing(false)
    setEditMode("write")
  }

  function startEditing() {
    setEditMode("write")
    setEditing(true)
  }

  const indent = INDENT_PX[Math.min(depth, 3)]
  const hasChildren = node.children.length > 0

  if (editing) {
    return (
      <div className="rounded-lg border p-3 space-y-3" style={indent > 0 ? { marginLeft: indent } : undefined}>
        <div className="flex justify-end">
          <WritePreviewToggle mode={editMode} onChange={setEditMode} />
        </div>
        <Textarea
          value={bodyMd}
          onChange={(e) => setBodyMd(e.target.value)}
          onKeyDown={(e) => {
            // Cmd/Ctrl+Enter saves; plain Enter inserts a newline.
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault()
              if (bodyMd.trim()) handleSave()
            }
            if (e.key === "Escape") handleCancel()
          }}
          rows={4}
          autoFocus
          className={cn(editMode === "preview" && "hidden")}
        />
        {editMode === "preview" && <MarkdownPreview body={bodyMd} />}
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
    <>
      <div
        className={cn(
          "group rounded-lg border p-3 space-y-1 transition-colors duration-1000",
          isHighlighted && "border-primary/40 bg-primary/10 duration-0",
        )}
        style={indent > 0 ? { marginLeft: indent } : undefined}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="prose prose-sm max-w-none flex-1">
            <Markdown>{node.body_md}</Markdown>
          </div>
          <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
            <Button
              size="icon-xs"
              variant="ghost"
              onClick={() => setReplying(!replying)}
              title="Reply"
            >
              <MessageSquare className="size-3.5" />
            </Button>
            <Button
              size="icon-xs"
              variant="ghost"
              onClick={startEditing}
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
                    {hasChildren
                      ? "This will delete this breadcrumb and all its replies. This action cannot be undone."
                      : "This will permanently delete this breadcrumb. This action cannot be undone."}
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
          {formatDate(node.created_at)}
          {node.updated_at && <> &middot; edited</>}
        </time>
        {removeMutation.error && (
          <p className="text-sm text-destructive">
            {removeMutation.error.message}
          </p>
        )}
      </div>

      {replying && (
        <div style={{ marginLeft: INDENT_PX[Math.min(depth + 1, 3)] }} className="mt-2">
          <AddBreadcrumbForm
            themeId={themeId}
            parentId={node.id}
            onCancel={() => setReplying(false)}
          />
        </div>
      )}

      {node.children.map((child) => (
        <BreadcrumbItem key={child.id} node={child} themeId={themeId} depth={depth + 1} />
      ))}
    </>
  )
}
