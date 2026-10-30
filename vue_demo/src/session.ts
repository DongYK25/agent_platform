import { reactive } from 'vue'

const TOKEN_KEY = 'agent_platform_token'
const NAME_KEY = 'agent_platform_username'

export const session = reactive({
  token: localStorage.getItem(TOKEN_KEY) ?? '',
  username: localStorage.getItem(NAME_KEY) ?? '',
})

export function setSession(token: string, username: string) {
  session.token = token
  session.username = username
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(NAME_KEY, username)
}

export function clearSession() {
  session.token = ''
  session.username = ''
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(NAME_KEY)
}
