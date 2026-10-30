import { request } from './http'
import type { User, UserCreate, UserUpdate } from './types'

export function listUsers(offset = 0, limit = 10) {
  const query = new URLSearchParams({ offset: String(offset), limit: String(limit) })
  return request<User[]>(`/users/?${query.toString()}`)
}

export function createUser(body: UserCreate) {
  return request<User>('/users/', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateUser(id: number, body: UserUpdate) {
  return request<User>(`/users/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export function deleteUser(id: number) {
  return request<null>(`/users/${id}`, { method: 'DELETE' })
}
