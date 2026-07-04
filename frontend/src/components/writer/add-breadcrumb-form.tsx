import { useRef, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { ImagePlus, Plus, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { createBreadcrumb, uploadImage } from "@/lib/api"
import { cn } from "@/lib/utils"
import { useDraft } from "@/hooks/use-draft"
import { useHighlight } from "./highlight-context"
import {
  MarkdownPreview,
  WritePreviewToggle,
  type WritePreviewMode,
} from "./markdown-field"

interface AddBreadcrumbFormProps {
  themeId: number
  parentId?: number
  onCancel?: () => void
}

export function AddBreadcrumbForm({ themeId, parentId, onCancel }: AddBreadcrumbFormProps) {
  const queryClient = useQueryClient()
  const { highlight } = useHighlight()
  // Persist top-level drafts per theme; replies are transient and don't own one.
  const [bodyMd, setBodyMd, clearDraft] = useDraft(
    `draft:breadcrumb:${themeId}`,
    { enabled: !parentId },
  )
  const [uploading, setUploading] = useState(false)
  const [mode, setMode] = useState<WritePreviewMode>("write")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const mutation = useMutation({
    mutationFn: (data: { body_md: string; parent_id?: number }) =>
      createBreadcrumb(themeId, data),
    onSuccess: (created) => {
      queryClient.invalidateQueries({
        queryKey: ["themes", themeId, "breadcrumbs"],
      })
      // The freshly added card highlights itself in the list — that entry
      // animation is the primary "saved" signal (see #80).
      highlight(created.id)
      clearDraft()
      if (parentId) {
        onCancel?.()
      } else {
        textareaRef.current?.focus()
      }
    },
  })

  function submit() {
    if (!bodyMd.trim() || mutation.isPending) return
    mutation.mutate({
      body_md: bodyMd.trim(),
      ...(parentId ? { parent_id: parentId } : {}),
    })
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    submit()
  }

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = "" // reset so same file can be re-selected
    setUploading(true)
    try {
      const { url } = await uploadImage(file)
      const textarea = textareaRef.current
      const pos = textarea?.selectionStart ?? bodyMd.length
      const markdown = `![](${url})\n`
      setBodyMd(bodyMd.slice(0, pos) + markdown + bodyMd.slice(pos))
    } catch (err) {
      mutation.reset()
      alert(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setUploading(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Cmd+Enter (macOS) / Ctrl+Enter saves; plain Enter inserts a newline.
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      submit()
    }
    if (e.key === "Escape" && onCancel) {
      onCancel()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileSelect}
      />
      <div className="flex justify-end">
        <WritePreviewToggle mode={mode} onChange={setMode} />
      </div>
      {/* Textarea stays mounted (just hidden) in preview so content, cursor,
          and the Cmd+Enter binding survive the toggle. */}
      <Textarea
        ref={textareaRef}
        value={bodyMd}
        onChange={(e) => setBodyMd(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={parentId ? "Reply..." : "Add a breadcrumb... (supports markdown)"}
        rows={parentId ? 2 : 3}
        autoFocus={!!parentId}
        className={cn(mode === "preview" && "hidden")}
      />
      {mode === "preview" && (
        <div className="rounded-md border p-3">
          <MarkdownPreview body={bodyMd} />
        </div>
      )}
      {mutation.error && (
        <p className="text-sm text-destructive">{mutation.error.message}</p>
      )}
      <div className="flex items-center gap-3">
        <Button
          type="submit"
          size="sm"
          disabled={mutation.isPending || !bodyMd.trim()}
        >
          <Plus className="size-4" />
          {mutation.isPending ? "Adding..." : parentId ? "Reply" : "Add Breadcrumb"}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={uploading}
          onClick={() => fileInputRef.current?.click()}
        >
          <ImagePlus className="size-4" />
          {uploading ? "Uploading..." : "Image"}
        </Button>
        {onCancel && (
          <Button type="button" size="sm" variant="outline" onClick={onCancel}>
            <X className="size-4" />
            Cancel
          </Button>
        )}
      </div>
      {!parentId && (
        <p className="text-xs text-muted-foreground">
          {navigator.platform.startsWith("Mac") ? "⌘" : "Ctrl"}+Enter to save
        </p>
      )}
    </form>
  )
}
