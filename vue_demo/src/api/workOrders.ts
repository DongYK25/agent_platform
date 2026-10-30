import { request } from './http'
import type { WorkOrder, WorkOrderCreate, WorkOrderUpdate } from './types'

export function listWorkOrders(offset = 0, limit = 10) {
  const query = new URLSearchParams({ offset: String(offset), limit: String(limit) })
  return request<WorkOrder[]>(`/work_orders/?${query.toString()}`)
}

export function getWorkOrder(id: number) {
  return request<WorkOrder>(`/work_orders/${id}`)
}

export function createWorkOrder(body: WorkOrderCreate) {
  return request<WorkOrder>('/work_orders/', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateWorkOrder(id: number, body: WorkOrderUpdate) {
  return request<WorkOrder>(`/work_orders/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export function deleteWorkOrder(id: number) {
  return request<null>(`/work_orders/${id}`, { method: 'DELETE' })
}
