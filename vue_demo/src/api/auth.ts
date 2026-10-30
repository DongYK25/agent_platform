import { request } from './http'

/** 登录参数在查询串上，与当前接口定义一致。 */
export function login(username: string, password: string) {
  const query = new URLSearchParams({ username, password })
  return request<string>(`/users/login?${query.toString()}`, { method: 'POST' })
}
