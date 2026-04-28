import { Link, createFileRoute, useNavigate } from '@tanstack/react-router'
import { CalendarClock, FolderOpen, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'

import { Button } from '#/components/ui/button'
import { Spinner } from '#/components/ui/spinner'
import { CreateProjectDialog } from '#/features/projects/CreateProjectDialog'
import { useDeleteProject, useProjects } from '#/features/projects/hooks'
import type { Project } from '#/features/projects/types'
import { useAuth } from '#/features/auth/AuthProvider'
import { readErrorMessage } from '#/lib/api'

export const Route = createFileRoute('/_app/dashboard')({ component: DashboardPage })

function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const projectsQuery = useProjects()
  const deleteProject = useDeleteProject()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const greeting = user?.full_name?.split(' ')[0] ?? user?.email ?? 'there'

  async function onDelete(project: Project) {
    if (!confirm(`Delete "${project.name}"? This removes its datasets too.`)) return
    setDeleteError(null)
    try {
      await deleteProject.mutateAsync(project.id)
    } catch (err) {
      setDeleteError(await readErrorMessage(err))
    }
  }

  return (
    <div className="page-wrap py-10">
      <header className="rise-in mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <span className="island-kicker">Workspace</span>
          <h1 className="display-title mt-1 text-3xl font-bold text-(--sea-ink) md:text-4xl">
            Welcome, {greeting}
          </h1>
          <p className="mt-2 max-w-xl text-(--sea-ink-soft)">
            Spin up a project, ingest your datasets, and run KH-weighted oil splitting.
          </p>
        </div>
        <Button onClick={() => setDialogOpen(true)} size="lg">
          <Plus size={18} />
          New project
        </Button>
      </header>

      {deleteError ? (
        <div
          role="alert"
          className="mb-4 rounded-xl border border-red-200/70 bg-red-50/80 px-3 py-2 text-sm text-red-700"
        >
          {deleteError}
        </div>
      ) : null}

      {projectsQuery.isPending ? (
        <div className="flex min-h-[40vh] items-center justify-center text-(--sea-ink-soft)">
          <Spinner size="md" />
          <span className="ml-3">Loading projects…</span>
        </div>
      ) : projectsQuery.isError ? (
        <div className="rounded-2xl border border-red-200/70 bg-red-50/80 p-5 text-sm text-red-700">
          Couldn’t load your projects: {projectsQuery.error?.message ?? 'unknown error'}
        </div>
      ) : projectsQuery.data && projectsQuery.data.length > 0 ? (
        <section className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {projectsQuery.data.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onOpen={() =>
                navigate({
                  to: '/projects/$projectId',
                  params: { projectId: String(project.id) },
                })
              }
              onDelete={() => onDelete(project)}
              deleting={
                deleteProject.isPending && deleteProject.variables === project.id
              }
            />
          ))}
        </section>
      ) : (
        <EmptyState onCreate={() => setDialogOpen(true)} />
      )}

      <CreateProjectDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreated={(id) =>
          navigate({
            to: '/projects/$projectId',
            params: { projectId: String(id) },
          })
        }
      />
    </div>
  )
}

function ProjectCard({
  project,
  onOpen,
  onDelete,
  deleting,
}: {
  project: Project
  onOpen: () => void
  onDelete: () => void
  deleting: boolean
}) {
  const updated = new Date(project.updated_at)

  return (
    <article className="feature-card group flex flex-col rounded-3xl border border-(--line) p-5">
      <div className="flex items-start justify-between gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-2xl bg-(--surface-strong) text-(--lagoon-deep) shadow-[0_1px_0_var(--inset-glint)_inset]">
          <FolderOpen size={20} />
        </span>
        <button
          type="button"
          onClick={onDelete}
          disabled={deleting}
          aria-label={`Delete ${project.name}`}
          className="grid h-8 w-8 place-items-center rounded-full text-(--sea-ink-soft) opacity-0 transition-all group-hover:opacity-100 hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {deleting ? <Spinner size="sm" /> : <Trash2 size={16} />}
        </button>
      </div>

      <h3 className="display-title mt-3 text-base font-bold text-(--sea-ink)">
        {project.name}
      </h3>
      {project.description ? (
        <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-(--sea-ink-soft)">
          {project.description}
        </p>
      ) : (
        <p className="mt-1.5 text-sm italic text-(--sea-ink-soft)/70">
          No description yet.
        </p>
      )}

      <div className="mt-4 flex items-center gap-1.5 text-xs text-(--sea-ink-soft)">
        <CalendarClock size={12} />
        <span>Updated {updated.toLocaleDateString()}</span>
      </div>

      <div className="mt-4 flex justify-end">
        <Link
          to="/projects/$projectId"
          params={{ projectId: String(project.id) }}
          className="text-sm font-semibold no-underline text-(--lagoon-deep) hover:text-(--lagoon)"
          onClick={(e) => {
            e.preventDefault()
            onOpen()
          }}
        >
          Open →
        </Link>
      </div>
    </article>
  )
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="island-shell rise-in mx-auto max-w-xl rounded-3xl p-10 text-center">
      <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-(--surface-strong) text-(--lagoon-deep) shadow-[0_1px_0_var(--inset-glint)_inset]">
        <FolderOpen size={22} />
      </div>
      <h2 className="display-title text-xl font-bold text-(--sea-ink)">
        No projects yet
      </h2>
      <p className="mx-auto mt-2 max-w-sm text-sm text-(--sea-ink-soft)">
        Create a project to start ingesting markers, completions, and production data
        for your splitting runs.
      </p>
      <div className="mt-5 flex justify-center">
        <Button onClick={onCreate}>
          <Plus size={16} />
          Create your first project
        </Button>
      </div>
    </div>
  )
}
