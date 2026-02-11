import { useEffect, useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import Markdown from "react-markdown"
import { Pencil, Check, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
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
import { updateTheme, deleteTheme } from "@/lib/api"
import type { ThemePublic } from "@/lib/types"

interface ThemeHeaderEditorProps {
  theme: ThemePublic
}

function parseTags(input: string): { name: string }[] {
  return input
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean)
    .map((name) => ({ name }))
}

function tagsToString(tags: { name: string }[]): string {
  return tags.map((t) => t.name).join(", ")
}

export function ThemeHeaderEditor({ theme }: ThemeHeaderEditorProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [editing, setEditing] = useState(false)
  const [body, setBody] = useState(theme.body_md)
  const [tags, setTags] = useState(tagsToString(theme.tags))

  // Sync local state when theme prop changes (e.g. after mutation + refetch)
  useEffect(() => {
    if (!editing) {
      setBody(theme.body_md)
      setTags(tagsToString(theme.tags))
    }
  }, [theme.body_md, theme.tags, editing])

  const updateMutation = useMutation({
    mutationFn: (data: Parameters<typeof updateTheme>[1]) =>
      updateTheme(theme.id, data),
    onSuccess: (updated) => {
      queryClient.setQueryData(["themes", theme.id], updated)
      queryClient.invalidateQueries({ queryKey: ["themes"] })
      setEditing(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteTheme(theme.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["themes"] })
      navigate({ to: "/writer" })
    },
  })

  const toggleVisibility = useMutation({
    mutationFn: () =>
      updateTheme(theme.id, {
        visibility: theme.visibility === "published" ? "draft" : "published",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["themes"] })
    },
  })

  function handleSave() {
    if (!body.trim()) return
    updateMutation.mutate({
      body_md: body.trim(),
      tags: parseTags(tags),
    })
  }

  function handleCancel() {
    setBody(theme.body_md)
    setTags(tagsToString(theme.tags))
    setEditing(false)
  }

  if (editing) {
    return (
      <div className="space-y-4 rounded-lg border p-4">
        <div className="space-y-2">
          <Label htmlFor="edit-body">Body</Label>
          <Textarea
            id="edit-body"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={5}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="edit-tags">Tags (comma-separated)</Label>
          <Input
            id="edit-tags"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
          />
        </div>

        {updateMutation.error && (
          <p className="text-sm text-destructive">
            {updateMutation.error.message}
          </p>
        )}

        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={handleSave}
            disabled={updateMutation.isPending || !body.trim()}
          >
            <Check className="size-4" />
            {updateMutation.isPending ? "Saving..." : "Save"}
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
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div className="prose prose-sm max-w-none">
          <Markdown>{theme.body_md}</Markdown>
        </div>
        <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
          <Pencil className="size-4" />
          Edit
        </Button>
      </div>

      {theme.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {theme.tags.map((tag) => (
            <Badge key={tag.id} variant="outline" className="text-xs">
              {tag.name}
            </Badge>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between rounded-lg border p-3">
        <div className="flex items-center gap-3">
          <Label htmlFor="publish-toggle" className="text-sm cursor-pointer">
            Publish
          </Label>
          <Switch
            id="publish-toggle"
            checked={theme.visibility === "published"}
            onCheckedChange={() => toggleVisibility.mutate()}
            disabled={toggleVisibility.isPending}
          />
          <Badge
            variant={theme.visibility === "published" ? "default" : "secondary"}
          >
            {theme.visibility}
          </Badge>
        </div>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              size="sm"
              variant="destructive"
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete Theme"}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete this theme?</AlertDialogTitle>
              <AlertDialogDescription>
                This will permanently delete this theme and all its breadcrumbs.
                This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={() => deleteMutation.mutate()}>
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {(toggleVisibility.error || deleteMutation.error) && (
        <p className="text-sm text-destructive">
          {(toggleVisibility.error ?? deleteMutation.error)?.message}
        </p>
      )}
    </div>
  )
}
