export type Project = {
  id: number
  owner_id: number
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export type ProjectCreatePayload = {
  name: string
  description?: string | null
}

export type ProjectUpdatePayload = {
  name?: string
  description?: string | null
}
