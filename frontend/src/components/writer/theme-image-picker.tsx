import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Sparkles, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
  clearThemeImage,
  commitThemeImage,
  generateThemeImage,
} from "@/lib/api"
import type { ThemePublic } from "@/lib/types"

interface ThemeImagePickerProps {
  theme: ThemePublic
}

export function ThemeImagePicker({ theme }: ThemeImagePickerProps) {
  const queryClient = useQueryClient()
  const [candidates, setCandidates] = useState<string[]>([])
  const [prompt, setPrompt] = useState<string | null>(null)

  const generate = useMutation({
    mutationFn: () => generateThemeImage(theme.id),
    onSuccess: (res) => {
      setCandidates(res.candidates)
      setPrompt(res.prompt)
    },
  })

  const commit = useMutation({
    mutationFn: (sourceUrl: string) => commitThemeImage(theme.id, sourceUrl),
    onSuccess: (updated) => {
      queryClient.setQueryData(["themes", theme.id], updated)
      queryClient.invalidateQueries({ queryKey: ["themes"] })
      setCandidates([])
      setPrompt(null)
    },
  })

  const clearImage = useMutation({
    mutationFn: () => clearThemeImage(theme.id),
    onSuccess: (updated) => {
      queryClient.setQueryData(["themes", theme.id], updated)
      queryClient.invalidateQueries({ queryKey: ["themes"] })
    },
  })

  return (
    <div className="space-y-3 rounded-lg border p-4">
      <div className="flex items-center justify-between">
        <Label className="text-sm">Cover image</Label>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => generate.mutate()}
            disabled={generate.isPending || commit.isPending}
          >
            <Sparkles className="size-4" />
            {generate.isPending
              ? "Generating..."
              : theme.image_url
                ? "Regenerate"
                : "Generate"}
          </Button>
          {theme.image_url && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => clearImage.mutate()}
              disabled={clearImage.isPending}
            >
              <Trash2 className="size-4" />
              Remove
            </Button>
          )}
        </div>
      </div>

      {theme.image_url && candidates.length === 0 && (
        <img
          src={theme.image_url}
          alt=""
          className="w-32 h-32 rounded object-cover"
        />
      )}

      {generate.error && (
        <p className="text-sm text-destructive">{generate.error.message}</p>
      )}
      {commit.error && (
        <p className="text-sm text-destructive">{commit.error.message}</p>
      )}
      {clearImage.error && (
        <p className="text-sm text-destructive">{clearImage.error.message}</p>
      )}

      {candidates.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">
            Click one to save. {prompt && <span className="italic">Prompt: {prompt}</span>}
          </p>
          <div className="grid grid-cols-2 gap-2">
            {candidates.map((url) => (
              <button
                key={url}
                type="button"
                onClick={() => commit.mutate(url)}
                disabled={commit.isPending}
                className="group relative overflow-hidden rounded border hover:ring-2 hover:ring-primary transition"
              >
                <img
                  src={url}
                  alt=""
                  className="w-full aspect-square object-cover group-hover:opacity-90"
                />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
