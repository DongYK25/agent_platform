import { createApp } from 'vue'
import App from './App.vue'
import { setUnauthorizedHandler } from './api/http'
import { router } from './router'
import { clearSession } from './session'
import './style.css'

setUnauthorizedHandler(() => {
  clearSession()
  if (router.currentRoute.value.path !== '/login') {
    router.push('/login')
  }
})

createApp(App).use(router).mount('#app')
