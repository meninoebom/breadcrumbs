import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Plus, Sparkles, X } from "lucide-react"
import { fetchTags } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface TagInputProps {
  value: string[]
  onChange: (tags: string[]) => void
  placeholder?: string
  id?: string
  disabled?: boolean
  className?: string
  aiSuggestedTags?: string[]
}

/** Normalize a raw tag string: trim, lowercase, whitespace to hyphens. */
function normalizeTag(raw: string): string {
  return raw.trim().toLowerCase().replace(/\s+/g, "-")
}

/**
 * Parse raw input (possibly comma-separated) into normalized,
 * deduplicated tags, excluding any already selected.
 */
function normalizeTags(raw: string, existing: string[]): string[] {
  const existingSet = new Set(existing)
  return raw
    .split(",")
    .map(normalizeTag)
    .filter((t) => t.length > 0 && !existingSet.has(t))
    .filter((t, i, arr) => arr.indexOf(t) === i)
}

export function TagInput({
  value,
  onChange,
  placeholder = "Add tags...",
  id,
  disabled,
  className,
  aiSuggestedTags,
}: TagInputProps) {
  const aiSuggestedSet = useMemo(
    () => new Set(aiSuggestedTags ?? []),
    [aiSuggestedTags],
  )
  const [inputValue, setInputValue] = useState("")
  const [isOpen, setIsOpen] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownId = useRef(
    `tag-suggestions-${Math.random().toString(36).slice(2, 8)}`,
  ).current

  const { data: allTags } = useQuery({
    queryKey: ["tags"],
    queryFn: fetchTags,
  })

  const existingTagNames = useMemo(
    () => new Set(allTags?.map((t) => t.name) ?? []),
    [allTags],
  )

  // Filter suggestions: exclude selected, match substring, prefix first
  const suggestions = useMemo(() => {
    const query = normalizeTag(inputValue)
    if (!query || !allTags) return []

    const selectedSet = new Set(value)
    const matches = allTags.filter(
      (t) => !selectedSet.has(t.name) && t.name.includes(query),
    )
    const prefix = matches
      .filter((t) => t.name.startsWith(query))
      .sort((a, b) => a.name.localeCompare(b.name))
    const rest = matches
      .filter((t) => !t.name.startsWith(query))
      .sort((a, b) => a.name.localeCompare(b.name))

    return [...prefix, ...rest]
  }, [inputValue, allTags, value])

  const showCreateRow = useMemo(() => {
    const normalized = normalizeTag(inputValue)
    return (
      normalized.length > 0 &&
      !suggestions.some((s) => s.name === normalized) &&
      !value.includes(normalized)
    )
  }, [inputValue, suggestions, value])

  const totalItems = suggestions.length + (showCreateRow ? 1 : 0)

  useEffect(() => {
    setHighlightedIndex(-1)
  }, [suggestions.length, showCreateRow])

  const addTag = useCallback(
    (name: string) => {
      const normalized = normalizeTag(name)
      if (normalized && !value.includes(normalized)) {
        onChange([...value, normalized])
      }
      setInputValue("")
      setIsOpen(false)
      setHighlightedIndex(-1)
    },
    [value, onChange],
  )

  const removeTag = useCallback(
    (name: string) => {
      onChange(value.filter((t) => t !== name))
    },
    [value, onChange],
  )

  const commitInput = useCallback(() => {
    const tags = normalizeTags(inputValue, value)
    if (tags.length > 0) {
      onChange([...value, ...tags])
    }
    setInputValue("")
    setIsOpen(false)
    setHighlightedIndex(-1)
  }, [inputValue, value, onChange])

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    switch (e.key) {
      case ",":
        e.preventDefault()
        commitInput()
        break
      case "Enter":
        e.preventDefault()
        if (isOpen && highlightedIndex >= 0) {
          if (highlightedIndex < suggestions.length) {
            addTag(suggestions[highlightedIndex].name)
          } else if (showCreateRow) {
            addTag(inputValue)
          }
        } else {
          commitInput()
        }
        break
      case "Backspace":
        if (inputValue === "" && value.length > 0) {
          removeTag(value[value.length - 1])
        }
        break
      case "Escape":
        setIsOpen(false)
        setHighlightedIndex(-1)
        break
      case "ArrowDown":
        e.preventDefault()
        if (totalItems > 0) {
          setIsOpen(true)
          setHighlightedIndex((prev) =>
            prev < totalItems - 1 ? prev + 1 : 0,
          )
        }
        break
      case "ArrowUp":
        e.preventDefault()
        if (totalItems > 0 && isOpen) {
          setHighlightedIndex((prev) =>
            prev > 0 ? prev - 1 : totalItems - 1,
          )
        }
        break
      case "Tab":
        if (isOpen && highlightedIndex >= 0) {
          e.preventDefault()
          if (highlightedIndex < suggestions.length) {
            addTag(suggestions[highlightedIndex].name)
          } else if (showCreateRow) {
            addTag(inputValue)
          }
        } else if (inputValue.trim()) {
          commitInput()
        }
        break
    }
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value
    setInputValue(val)
    setIsOpen(normalizeTag(val).length > 0)
    setHighlightedIndex(-1)
  }

  function handlePaste(e: React.ClipboardEvent<HTMLInputElement>) {
    e.preventDefault()
    const pasted = e.clipboardData.getData("text")
    const tags = normalizeTags(pasted, value)
    if (tags.length > 0) {
      onChange([...value, ...tags])
    }
    setInputValue("")
    setIsOpen(false)
  }

  function handleBlur() {
    commitInput()
  }

  function handleContainerClick() {
    inputRef.current?.focus()
  }

  const highlightedId =
    highlightedIndex >= 0
      ? `${dropdownId}-option-${highlightedIndex}`
      : undefined

  return (
    <div className={cn("relative", className)}>
      <div
        role="combobox"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-owns={dropdownId}
        onClick={handleContainerClick}
        className={cn(
          "flex flex-wrap gap-1.5 items-center rounded-md border bg-background px-3 py-2 text-sm",
          "ring-offset-background focus-within:outline-none focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2",
          disabled && "cursor-not-allowed opacity-50",
        )}
      >
        {value.map((tag) => (
          <Badge
            key={tag}
            variant={existingTagNames.has(tag) ? "secondary" : "outline"}
            className={cn(
              "gap-1 pr-1",
              !existingTagNames.has(tag) && "border-dashed",
            )}
          >
            {aiSuggestedSet.has(tag) && (
              <Sparkles className="size-3 text-muted-foreground" aria-label="AI suggested" />
            )}
            {tag}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                removeTag(tag)
                inputRef.current?.focus()
              }}
              className="rounded-sm hover:bg-muted-foreground/20 p-0.5"
              aria-label={`Remove tag ${tag}`}
              disabled={disabled}
            >
              <X className="size-3" />
            </button>
          </Badge>
        ))}
        <input
          ref={inputRef}
          id={id}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          onBlur={handleBlur}
          placeholder={value.length === 0 ? placeholder : undefined}
          disabled={disabled}
          className="flex-1 min-w-[120px] bg-transparent outline-none placeholder:text-muted-foreground"
          aria-autocomplete="list"
          aria-controls={dropdownId}
          aria-activedescendant={highlightedId}
        />
      </div>

      {isOpen && totalItems > 0 && (
        <div
          id={dropdownId}
          role="listbox"
          className="absolute z-50 mt-1 w-full rounded-md border bg-popover p-1 shadow-md"
        >
          {suggestions.map((tag, index) => (
            <div
              key={tag.id}
              id={`${dropdownId}-option-${index}`}
              role="option"
              aria-selected={highlightedIndex === index}
              onMouseDown={(e) => {
                e.preventDefault()
                addTag(tag.name)
                inputRef.current?.focus()
              }}
              className={cn(
                "cursor-pointer rounded-sm px-2 py-1.5 text-sm",
                highlightedIndex === index
                  ? "bg-accent text-accent-foreground"
                  : "hover:bg-accent/50",
              )}
            >
              {tag.name}
            </div>
          ))}
          {showCreateRow && (
            <div
              id={`${dropdownId}-option-${suggestions.length}`}
              role="option"
              aria-selected={highlightedIndex === suggestions.length}
              onMouseDown={(e) => {
                e.preventDefault()
                addTag(inputValue)
                inputRef.current?.focus()
              }}
              className={cn(
                "cursor-pointer rounded-sm px-2 py-1.5 text-sm flex items-center gap-1.5 text-muted-foreground",
                highlightedIndex === suggestions.length
                  ? "bg-accent text-accent-foreground"
                  : "hover:bg-accent/50",
              )}
            >
              <Plus className="size-3.5" />
              Create &ldquo;{normalizeTag(inputValue)}&rdquo;
            </div>
          )}
        </div>
      )}
    </div>
  )
}
