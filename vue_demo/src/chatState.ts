import { ref } from 'vue'

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
}

export const messages = ref<ChatMessage[]>([])

let seed = 0

export function nextChatId() {
  seed += 1
  return seed
}
