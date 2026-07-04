import { useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { TagInput } from "@/components/ui/tag-input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { createTheme, suggestTags, updateTheme } from "@/lib/api"
import { useDraft } from "@/hooks/use-draft"

interface CreateThemeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

type Phase = "compose" | "review-tags"

export function CreateThemeDialog({ open, onOpenChange }: CreateThemeDialogProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [body, setBody, clearBodyDraft] = useDraft("draft:new-theme")
  const [tags, setTags] = useState<string[]>([])
  const [phase, setPhase] = useState<Phase>("compose")
  const [createdThemeId, setCreatedThemeId] = useState<number | null>(null)
  const [aiSuggestedTags, setAiSuggestedTags] = useState<string[]>([])
  const [isSuggesting, setIsSuggesting] = useState(false)

  const createMutation = useMutation({
    mutationFn: createTheme,
    onSuccess: async (newTheme) => {
      // The composed body is now a persisted theme, so the draft has served
      // its purpose — clear it (and the field) before moving on.
      clearBodyDraft()
      setCreatedThemeId(newTheme.id)
      setIsSuggesting(true)
      setPhase("review-tags")

      try {
        const result = await suggestTags(newTheme.id)
        setTags(result.tags)
        setAiSuggestedTags(result.tags)
      } catch {
        // Suggestion failed — let writer add tags manually
      } finally {
        setIsSuggesting(false)
      }
    },
  })

  const saveMutation = useMutation({
    mutationFn: ({ themeId, tags }: { themeId: number; tags: string[] }) =>
      updateTheme(themeId, { tags: tags.map((name) => ({ name })) }),
    onSuccess: (_data, variables) => goToTheme(variables.themeId),
  })

  // Close the dialog and land in the new theme's editor. Every review-tags exit
  // routes through here — saving tags, skipping them, or dismissing the dialog —
  // so a created-but-untagged theme is never silently stranded.
  function goToTheme(themeId: number) {
    queryClient.invalidateQueries({ queryKey: ["themes"] })
    queryClient.invalidateQueries({ queryKey: ["tags"] })
    onOpenChange(false)
    resetForm()
    navigate({
      to: "/writer/themes/$themeId",
      params: { themeId: String(themeId) },
    })
  }

  function resetForm() {
    // Body is left to the draft hook: cancelling during compose keeps the
    // writing (restored on reopen); creating the theme clears it explicitly.
    setTags([])
    setPhase("compose")
    setCreatedThemeId(null)
    setAiSuggestedTags([])
    setIsSuggesting(false)
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (phase === "compose") {
      if (!body.trim()) return
      createMutation.mutate({ body_md: body.trim() })
    } else if (phase === "review-tags" && createdThemeId !== null) {
      saveMutation.mutate({ themeId: createdThemeId, tags })
    }
  }

  function handleOpenChange(open: boolean) {
    if (open) {
      onOpenChange(true)
      return
    }
    // Dismissing (escape / overlay / Cancel) after the theme exists must
    // acknowledge it — navigate to its editor instead of silently closing.
    if (phase === "review-tags" && createdThemeId !== null) {
      goToTheme(createdThemeId)
      return
    }
    resetForm()
    onOpenChange(false)
  }

  const isLoading = createMutation.isPending || isSuggesting || saveMutation.isPending

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>New Theme</DialogTitle>
            <DialogDescription>
              {phase === "compose"
                ? "Create a new theme to organize your breadcrumbs."
                : "Review the suggested tags. Remove any that don't fit."}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {phase === "compose" && (
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
            )}

            {phase === "review-tags" && (
              <div className="space-y-2">
                <Label htmlFor="tags" className="flex items-center gap-2">
                  Tags
                  {isSuggesting && (
                    <span className="flex items-center gap-1 text-xs text-muted-foreground font-normal">
                      <Loader2 className="size-3 animate-spin" />
                      Suggesting…
                    </span>
                  )}
                </Label>
                <TagInput
                  id="tags"
                  value={tags}
                  onChange={setTags}
                  placeholder="Add tags…"
                  disabled={isSuggesting}
                  aiSuggestedTags={aiSuggestedTags}
                />
              </div>
            )}
          </div>

          {(createMutation.error || saveMutation.error) && (
            <p className="text-sm text-destructive pb-2">
              {(createMutation.error ?? saveMutation.error)?.message}
            </p>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
            >
              {phase === "compose" ? "Cancel" : "Skip tags"}
            </Button>
            <Button
              type="submit"
              disabled={isLoading || (phase === "compose" && !body.trim())}
            >
              {phase === "compose"
                ? createMutation.isPending
                  ? "Creating…"
                  : "Create Theme"
                : saveMutation.isPending
                  ? "Saving…"
                  : "Save Tags"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
