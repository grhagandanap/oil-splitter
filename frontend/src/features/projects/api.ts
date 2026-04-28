import { api } from '#/lib/api'

import type { Project, ProjectCreatePayload, ProjectUpdatePayload } from './types'

export async function listProjects(): Promise<Project[]> {
  return api.get('projects').json<Project[]>()
}

export async function getProject(id: number): Promise<Project> {
  return api.get(`projects/${id}`).json<Project>()
}

export async function createProject(payload: ProjectCreatePayload): Promise<Project> {
  return api.post('projects', { json: payload }).json<Project>()
}

export async function updateProject(
  id: number,
  payload: ProjectUpdatePayload,
): Promise<Project> {
  return api.patch(`projects/${id}`, { json: payload }).json<Project>()
}

export async function deleteProject(id: number): Promise<void> {
  await api.delete(`projects/${id}`)
}
