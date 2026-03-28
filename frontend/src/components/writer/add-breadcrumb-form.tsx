import { useEffect, useRef, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Check, ImagePlus, Plus, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { createBreadcrumb, uploadImage } from "@/lib/api"

interface AddBreadcrumbFormProps {
  themeId: number
  parentId?: number
  onCancel?: () => void
}

export function AddBreadcrumbForm({ themeId, parentId, onCancel }: AddBreadcrumbFormProps) {
  const queryClient = useQueryClient()
  const [bodyMd, setBodyMd] = useState("")
  const [showSaved, setShowSaved] = useState(false)
  const [uploading, setUploading] = useState(false)
  const savedTimer = useRef<ReturnType<typeof setTimeout>>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (savedTimer.current) clearTimeout(savedTimer.current)
    }
  }, [])

  const mutation = useMutation({
    mutationFn: (data: { body_md: string; parent_id?: number }) =>
      createBreadcrumb(themeId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["themes", themeId, "breadcrumbs"],
      })
      setBodyMd("")
      setShowSaved(true)
      if (savedTimer.current) clearTimeout(savedTimer.current)
      savedTimer.current = setTimeout(() => setShowSaved(false), 2000)
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
    if (e.key === "Enter" && !e.shiftKey) {
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
      <Textarea
        ref={textareaRef}
        value={bodyMd}
        onChange={(e) => setBodyMd(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={parentId ? "Reply..." : "Add a breadcrumb... (supports markdown)"}
        rows={parentId ? 2 : 3}
        autoFocus={!!parentId}
      />
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
        {showSaved && (
          <span className="text-sm text-muted-foreground flex items-center gap-1 animate-in fade-in">
            <Check className="size-3.5" />
            Saved
          </span>
        )}
      </div>
      {!parentId && (
        <p className="text-xs text-muted-foreground">
          Enter to save &middot; Shift+Enter for new line
        </p>
      )}
    </form>
  )
}
