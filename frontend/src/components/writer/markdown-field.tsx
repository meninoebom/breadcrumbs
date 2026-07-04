import Markdown from "react-markdown"
import { cn } from "@/lib/utils"

export type WritePreviewMode = "write" | "preview"

/**
 * Small segmented control that flips an authoring textarea between raw-markdown
 * editing and a rendered preview. Buttons are type="button" so they never
 * submit the surrounding form.
 */
export function WritePreviewToggle({
  mode,
  onChange,
}: {
  mode: WritePreviewMode
  onChange: (mode: WritePreviewMode) => void
}) {
  return (
    <div className="inline-flex rounded-md border p-0.5 text-xs">
      {(["write", "preview"] as const).map((m) => (
        <button
          key={m}
          type="button"
          onClick={() => onChange(m)}
          className={cn(
            "rounded px-2 py-0.5 capitalize transition-colors",
            mode === m
              ? "bg-muted font-medium text-foreground"
              : "text-muted-foreground hover:text-foreground",
          )}
          aria-pressed={mode === m}
        >
          {m}
        </button>
      ))}
    </div>
  )
}

/**
 * Renders markdown with the same prose styling as the read view so a preview
 * matches what will actually be saved. Empty bodies show a muted placeholder.
 */
export function MarkdownPreview({
  body,
  className,
}: {
  body: string
  className?: string
}) {
  if (!body.trim()) {
    return (
      <p className="text-sm text-muted-foreground italic">Nothing to preview</p>
    )
  }
  return (
    <div className={cn("prose prose-sm max-w-none", className)}>
      <Markdown>{body}</Markdown>
    </div>
  )
}
