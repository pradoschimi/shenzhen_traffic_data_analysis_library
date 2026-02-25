/**
 * 用户登录状态管理（Pinia Store）
 * 管理 token、用户信息、登录/注册/登出操作。
 * 登录状态持久化在 localStorage 里，刷新页面不会丢失。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api'

export const useAuthStore = defineStore('auth', () => {
  // 从 localStorage 恢复上次的登录状态
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.is_admin === true)
  const username = computed(() => user.value?.username || '')
  const nickname = computed(() => user.value?.nickname || '')

  function setAuth(data) {
    token.value = data.access_token
    user.value = {
      user_id: data.user_id,
      username: data.username,
      nickname: data.nickname,
      is_admin: data.is_admin,
    }
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(user.value))
    localStorage.setItem('is_admin', String(data.is_admin))
  }

  async function login(username, password) {
    const data = await authApi.login({ username, password })
    setAuth(data)
    return data
  }

  async function register(username, password, nickname) {
    const data = await authApi.register({ username, password, nickname })
    setAuth(data)
    return data
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('is_admin')
  }

  return {
    token, user, isLoggedIn, isAdmin, username, nickname,
    login, register, logout,
  }
})
