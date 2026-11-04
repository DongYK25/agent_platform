import { request } from './http'

export interface ChatSession {
  id: string
  title?: string | null
  created_at?: string
  updated_at?: string
}

export interface HistoryItem {
  role: string
  content: string
}

export function listSessions(offset = 0, limit = 100) {
  const query = new URLSearchParams({ offset: String(offset), limit: String(limit) })
  return request<ChatSession[]>(`/agent/user_sessions?${query.toString()}`)
}

export function createSession() {
  return request<ChatSession>('/agent/user_sessions', { method: 'POST' })
}

export function renameSession(sessionUid: string, title: string) {
  return request<ChatSession>(`/agent/user_sessions/${sessionUid}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  })
}

export function deleteSession(sessionUid: string) {
  return request<null>(`/agent/user_sessions/${sessionUid}`, { method: 'DELETE' })
}

/** 点开某个对话窗口时调用一次。 */
export function getChatHistory(sessionUid: string) {
  const query = new URLSearchParams({ session_uid: sessionUid })
  return request<HistoryItem[]>(`/agent/chat_history?${query.toString()}`)
}

export function sendChat(msg: string, sessionUid: string) {
  return request<string>('/agent/chat', {
    method: 'POST',
    body: JSON.stringify({ msg, session_uid: sessionUid }),
  })
}
