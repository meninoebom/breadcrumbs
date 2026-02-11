import { useEffect, useRef, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Check, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { createBreadcrumb } from "@/lib/api"

interface AddBreadcrumbFormProps {
  themeId: number
}

export function AddBreadcrumbForm({ themeId }: AddBreadcrumbFormProps) {
  const queryClient = useQueryClient()
  const [bodyMd, setBodyMd] = useState("")
  const [showSaved, setShowSaved] = useState(false)
  const savedTimer = useRef<ReturnType<typeof setTimeout>>(null)

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (savedTimer.current) clearTimeout(savedTimer.current)
    }
  }, [])

  const mutation = useMutation({
    mutationFn: (data: { body_md: string }) => createBreadcrumb(themeId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["themes", themeId, "breadcrumbs"],
      })
      setBodyMd("")
      setShowSaved(true)
      if (savedTimer.current) clearTimeout(savedTimer.current)
      savedTimer.current = setTimeout(() => setShowSaved(false), 2000)
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!bodyMd.trim()) return
    mutation.mutate({ body_md: bodyMd.trim() })
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      if (bodyMd.trim()) mutation.mutate({ body_md: bodyMd.trim() })
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <Textarea
        value={bodyMd}
        onChange={(e) => setBodyMd(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Add a breadcrumb... (supports markdown)"
        rows={3}
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
          {mutation.isPending ? "Adding..." : "Add Breadcrumb"}
        </Button>
        {showSaved && (
          <span className="text-sm text-muted-foreground flex items-center gap-1 animate-in fade-in">
            <Check className="size-3.5" />
            Saved
          </span>
        )}
      </div>
      <p className="text-xs text-muted-foreground">
        Press Ctrl+Enter to save
      </p>
    </form>
  )
}
