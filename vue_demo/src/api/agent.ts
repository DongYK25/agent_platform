import { request } from './http'

/** data 是模型回复的文本。 */
export function sendChat(msg: string) {
  return request<string>('/agent/chat', {
    method: 'POST',
    body: JSON.stringify({ msg }),
  })
}
