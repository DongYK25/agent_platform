<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login } from '../api/auth'
import { errorMessage } from '../api/http'
import { createUser } from '../api/users'
import { setSession } from '../session'

const route = useRoute()
const router = useRouter()
const mode = ref<'login' | 'register'>('login')
const pending = ref(false)
const error = ref('')

const form = reactive({
  username: '',
  password: '',
  email: '',
  full_name: '',
})

function safeRedirect() {
  const value = route.query.redirect
  if (typeof value === 'string' && value.startsWith('/') && !value.startsWith('//')) return value
  return '/work-orders'
}

function switchMode(next: 'login' | 'register') {
  mode.value = next
  error.value = ''
}

async function submit() {
  error.value = ''
  const username = form.username.trim()
  if (username.length < 3) {
    error.value = '用户名至少 3 位，只能包含字母、数字和下划线'
    return
  }
  if (form.password.length < 6) {
    error.value = '密码至少 6 位'
    return
  }
  if (mode.value === 'register' && !form.email.trim()) {
    error.value = '请填写邮箱'
    return
  }

  pending.value = true
  try {
    if (mode.value === 'register') {
      await createUser({
        username,
        email: form.email.trim(),
        password: form.password,
        full_name: form.full_name.trim() || null,
      })
    }
    const token = await login(username, form.password)
    if (!token) {
      error.value = '登录没有返回 token'
      return
    }
    setSession(token, username)
    await router.push(safeRedirect())
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="login">
    <section class="login__intro">
      <p class="eyebrow">Agent Platform</p>
      <h1>把用户、工单和对话放在同一张工作台。</h1>
      <ul>
        <li>登录后管理账号</li>
        <li>创建并跟进工单</li>
        <li>直接和 Agent 对话</li>
      </ul>
    </section>

    <section class="login__panel">
      <div class="tabs" role="tablist">
        <button type="button" :class="{ 'is-active': mode === 'login' }" @click="switchMode('login')">
          登录
        </button>
        <button
          type="button"
          :class="{ 'is-active': mode === 'register' }"
          @click="switchMode('register')"
        >
          注册
        </button>
      </div>

      <form class="form" @submit.prevent="submit">
        <label class="field">
          <span>用户名</span>
          <input v-model="form.username" autocomplete="username" placeholder="字母、数字或下划线" />
        </label>
        <label v-if="mode === 'register'" class="field">
          <span>邮箱</span>
          <input v-model="form.email" type="email" autocomplete="email" placeholder="name@example.com" />
        </label>
        <label v-if="mode === 'register'" class="field">
          <span>姓名</span>
          <input v-model="form.full_name" autocomplete="name" placeholder="可选" />
        </label>
        <label class="field">
          <span>密码</span>
          <input
            v-model="form.password"
            type="password"
            :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
            placeholder="至少 6 位"
          />
        </label>
        <p v-if="error" class="form-error">{{ error }}</p>
        <button class="btn btn--primary" type="submit" :disabled="pending">
          {{ pending ? '提交中…' : mode === 'login' ? '进入工作台' : '注册并进入' }}
        </button>
      </form>
    </section>
  </div>
</template>
