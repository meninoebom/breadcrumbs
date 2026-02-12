import { createFileRoute } from "@tanstack/react-router"

export const Route = createFileRoute("/about")({
  component: About,
})

function About() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">About</h1>

      <div className="prose prose-sm max-w-none space-y-4">
        <p>
          I'm Brandon. I build things and think about building things, which
          sometimes feels like the same activity. I'm also interested in
          consciousness and mind, football (which Americans call soccer),
          music, dance, and how human beings come back together. To name a
          few. All of it shows up here.
        </p>
        <p>
          Breadcrumbs is where I drop the small thoughts that fall out of
          all of that — observations, questions, half-formed ideas — before
          they evaporate. Think of it less like a blog and more like a
          notebook left open on the table. Not essays. Not tutorials. Just
          crumbs, organized into themes, dropped along the way.
        </p>
        <p>
          The format is inspired in part by Alex Komoroske's{" "}
          <a
            href="https://docs.google.com/document/d/1x8z6k07JqXTVIRVNr1S_7wYVl5L7IpX14gXxU1UBrGk/edit"
            target="_blank"
            rel="noopener noreferrer"
          >
            Bits and Bobs
          </a>
          {" "}— the idea that the interesting thoughts rarely arrive fully
          formed. They start as fragments. If you collect enough of them in
          one place, patterns emerge that you couldn't have planned.
        </p>
        <p className="text-muted-foreground italic">
          Eventually, these breadcrumbs will learn to talk back. For now,
          you're stuck reading.
        </p>
      </div>
    </div>
  )
}
