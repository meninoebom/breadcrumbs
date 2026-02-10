import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { createBreadcrumb } from "@/lib/api"

interface AddBreadcrumbFormProps {
  themeId: number
}

export function AddBreadcrumbForm({ themeId }: AddBreadcrumbFormProps) {
  const queryClient = useQueryClient()
  const [bodyMd, setBodyMd] = useState("")

  const mutation = useMutation({
    mutationFn: (data: { body_md: string }) => createBreadcrumb(themeId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["themes", themeId, "breadcrumbs"],
      })
      setBodyMd("")
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!bodyMd.trim()) return
    mutation.mutate({ body_md: bodyMd.trim() })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <Textarea
        value={bodyMd}
        onChange={(e) => setBodyMd(e.target.value)}
        placeholder="Add a breadcrumb... (supports markdown)"
        rows={3}
      />
      {mutation.error && (
        <p className="text-sm text-destructive">{mutation.error.message}</p>
      )}
      <Button
        type="submit"
        size="sm"
        disabled={mutation.isPending || !bodyMd.trim()}
      >
        <Plus className="size-4" />
        {mutation.isPending ? "Adding..." : "Add Breadcrumb"}
      </Button>
    </form>
  )
}
