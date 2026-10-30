<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { clearSession, session } from '../session'

const route = useRoute()
const router = useRouter()

const nav = [
  { to: '/work-orders', label: '工单', hint: '处理事项' },
  { to: '/users', label: '用户', hint: '账号' },
  { to: '/chat', label: '对话', hint: 'Agent' },
]

const initial = computed(() => (session.username || '?').slice(0, 1).toUpperCase())

function logout() {
  clearSession()
  router.push('/login')
}
</script>

<template>
  <div class="shell">
    <aside class="sider">
      <div class="brand">
        <span class="brand__mark">台</span>
        <div>
          <strong>工单台</strong>
          <small>Agent Platform</small>
        </div>
      </div>
      <nav class="nav">
        <RouterLink v-for="item in nav" :key="item.to" :to="item.to">
          <span>{{ item.label }}</span>
          <small>{{ item.hint }}</small>
        </RouterLink>
      </nav>
    </aside>

    <div class="workspace">
      <header class="topbar">
        <p>{{ route.meta.title }}</p>
        <div class="account">
          <span class="avatar">{{ initial }}</span>
          <span>{{ session.username }}</span>
          <button class="btn btn--ghost" type="button" @click="logout">退出</button>
        </div>
      </header>
      <main class="main" :class="{ 'main--fill': route.meta.fill }">
        <RouterView />
      </main>
    </div>
  </div>
</template>
