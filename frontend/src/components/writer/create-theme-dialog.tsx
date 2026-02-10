import { useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { createTheme } from "@/lib/api"

interface CreateThemeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

function parseTags(input: string): { name: string }[] {
  return input
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean)
    .map((name) => ({ name }))
}

export function CreateThemeDialog({ open, onOpenChange }: CreateThemeDialogProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [body, setBody] = useState("")
  const [tags, setTags] = useState("")

  const mutation = useMutation({
    mutationFn: createTheme,
    onSuccess: (newTheme) => {
      queryClient.invalidateQueries({ queryKey: ["themes"] })
      onOpenChange(false)
      resetForm()
      navigate({
        to: "/writer/themes/$themeId",
        params: { themeId: String(newTheme.id) },
      })
    },
  })

  function resetForm() {
    setBody("")
    setTags("")
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!body.trim()) return
    mutation.mutate({
      body_md: body.trim(),
      tags: tags.trim() ? parseTags(tags) : undefined,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>New Theme</DialogTitle>
            <DialogDescription>
              Create a new theme to organize your breadcrumbs.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="body">Body</Label>
              <Textarea
                id="body"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Write your thought..."
                rows={4}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="tags">Tags (comma-separated)</Label>
              <Input
                id="tags"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="e.g. react, architecture, patterns"
              />
            </div>
          </div>

          {mutation.error && (
            <p className="text-sm text-destructive pb-2">
              {mutation.error.message}
            </p>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending || !body.trim()}>
              {mutation.isPending ? "Creating..." : "Create Theme"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
