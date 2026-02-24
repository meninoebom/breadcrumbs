import { useState } from "react"
import { subscribe } from "@/lib/api"

export function SubscribeWidget() {
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle")
  const [errorMsg, setErrorMsg] = useState("")

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const email = new FormData(e.currentTarget).get("email") as string
    if (!email?.trim()) return

    setStatus("loading")
    setErrorMsg("")
    try {
      await subscribe(email.trim())
      setStatus("done")
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Something went wrong")
      setStatus("error")
    }
  }

  if (status === "done") {
    return (
      <div className="rounded-lg border bg-muted/30 px-6 py-5 text-center">
        <p className="text-sm text-foreground">Check your inbox.</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border bg-muted/30 px-6 py-5 space-y-3">
      <p className="text-sm text-muted-foreground italic">
        Every path leaves marks. A weekly letter of what surfaced here.
      </p>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          name="email"
          type="email"
          required
          placeholder="your@email.com"
          className="flex-1 h-9 rounded-md border bg-background px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        />
        <button
          type="submit"
          disabled={status === "loading"}
          className="h-9 px-4 rounded-md bg-foreground text-background text-sm font-medium hover:bg-foreground/90 disabled:opacity-50"
        >
          {status === "loading" ? "..." : "Follow"}
        </button>
      </form>
      {status === "error" && (
        <p className="text-xs text-destructive">{errorMsg}</p>
      )}
      <p className="text-xs text-muted-foreground/60">
        No tracking. Unsubscribe anytime.
      </p>
    </div>
  )
}
