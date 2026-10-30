import type { ResponseCommon } from './types'
import { session } from '../session'

/**
 * 所有接口都从这里出去。
 * 成功时拆掉 { code, msg, data }，调用方只拿到 data。
 * 401 交给 main.ts 注册的回调，用来退出登录。
 */
const BASE = import.meta.env.VITE_API_BASE || '/api'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

let onUnauthorized = () => {}

export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

export function errorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message
  return '操作失败'
}

function readMessage(body: unknown, fallback: string) {
  if (body && typeof body === 'object' && 'msg' in body && typeof body.msg === 'string') {
    return body.msg
  }
  if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
    return body.detail
  }
  return fallback
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (session.token) {
    headers.set('Authorization', `Bearer ${session.token}`)
  }

  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, '无法连接服务器')
  }

  const text = await response.text()
  let body: unknown = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = { msg: text }
    }
  }

  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/users/login')) {
      onUnauthorized()
    }
    throw new ApiError(response.status, readMessage(body, '请求失败'))
  }

  if (body && typeof body === 'object' && 'code' in body && 'data' in body) {
    const envelope = body as ResponseCommon<T>
    if (envelope.code >= 400) {
      throw new ApiError(envelope.code, envelope.msg || '请求失败')
    }
    return envelope.data
  }

  return body as T
}
