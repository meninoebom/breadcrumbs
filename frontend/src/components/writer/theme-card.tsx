import { Link } from "@tanstack/react-router"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { ThemePublic } from "@/lib/types"
import { formatDate } from "@/lib/utils"

interface ThemeCardProps {
  theme: ThemePublic
}

export function ThemeCard({ theme }: ThemeCardProps) {
  return (
    <Link
      to="/writer/themes/$themeId"
      params={{ themeId: String(theme.id) }}
      className="no-underline"
    >
      <Card className="transition-colors hover:border-foreground/20">
        <CardHeader>
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-base line-clamp-2">
              {theme.body_md.split("\n")[0] || "Untitled"}
            </CardTitle>
            <Badge
              variant={theme.visibility === "published" ? "default" : "secondary"}
            >
              {theme.visibility}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          {theme.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {theme.tags.map((tag) => (
                <Badge key={tag.id} variant="outline" className="text-xs">
                  {tag.name}
                </Badge>
              ))}
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            Created {formatDate(theme.created_at)}
            {theme.updated_at && <> &middot; Updated {formatDate(theme.updated_at)}</>}
          </p>
        </CardContent>
      </Card>
    </Link>
  )
}
