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
          sometimes feels like the same activity. Right now a lot of that
          building is happening at the intersection of movement, music, and
          technology. I'm working on instruments that listen to dancers and
          respond with sound, and writing about what I'm calling relational
          musicality — the idea that choreo-musical traditions like capoeira
          and house dance are sophisticated technologies for human coordination
          that we've mostly failed to recognize as such. I'm also interested
          in consciousness, philosophy of mind, football (which Americans call
          soccer), meditation, and how human beings can live well together.
          All of that and more could show up here.
        </p>
        <p>
          Breadcrumbs is where I drop the small thoughts that fall out of
          all of that. Observations, questions, half-formed ideas, before
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
          — the idea that the interesting thoughts rarely arrive fully
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
