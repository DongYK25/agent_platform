/** 与后端 ResponseCommon 对应。业务数据在 data 里。 */
export interface ResponseCommon<T> {
  code: number
  msg: string
  data: T
}

export interface User {
  id: number
  username: string
  email: string
  full_name?: string | null
  status?: string
  created_at?: string
}

export interface UserCreate {
  username: string
  email: string
  password: string
  full_name?: string | null
}

export interface UserUpdate {
  username?: string
  email?: string
  full_name?: string | null
  password?: string
}

export interface WorkOrder {
  id: number
  order_uuid?: string
  title: string
  content?: string | null
  status?: string
  order_type?: string | null
  priority?: string | null
  creator_id?: number
  handler_id?: number | null
  remark?: string | null
  created_at?: string
}

export interface WorkOrderCreate {
  title: string
  content?: string | null
  status?: string
  order_type?: string | null
  priority?: string | null
  handler_id?: number | null
  remark?: string | null
}

export interface WorkOrderUpdate extends WorkOrderCreate {
  id: number
}
