import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  createProject,
  deleteProject,
  getProject,
  listProjects,
  updateProject,
} from './api'
import type { Project, ProjectCreatePayload, ProjectUpdatePayload } from './types'

export const projectKeys = {
  all: ['projects'] as const,
  list: () => [...projectKeys.all, 'list'] as const,
  detail: (id: number) => [...projectKeys.all, 'detail', id] as const,
}

export function useProjects() {
  return useQuery<Project[]>({
    queryKey: projectKeys.list(),
    queryFn: listProjects,
  })
}

export function useProject(id: number | undefined) {
  return useQuery<Project>({
    queryKey: id !== undefined ? projectKeys.detail(id) : ['projects', 'detail', 'noop'],
    queryFn: () => getProject(id as number),
    enabled: typeof id === 'number',
  })
}

export function useCreateProject() {
  const qc = useQueryClient()
  return useMutation<Project, Error, ProjectCreatePayload>({
    mutationFn: createProject,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: projectKeys.list() })
    },
  })
}

export function useUpdateProject(id: number) {
  const qc = useQueryClient()
  return useMutation<Project, Error, ProjectUpdatePayload>({
    mutationFn: (payload) => updateProject(id, payload),
    onSuccess: (project) => {
      qc.setQueryData(projectKeys.detail(id), project)
      void qc.invalidateQueries({ queryKey: projectKeys.list() })
    },
  })
}

export function useDeleteProject() {
  const qc = useQueryClient()
  return useMutation<void, Error, number>({
    mutationFn: deleteProject,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: projectKeys.list() })
    },
  })
}
