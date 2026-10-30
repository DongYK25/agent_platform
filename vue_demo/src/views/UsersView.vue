<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { errorMessage } from '../api/http'
import type { User, UserUpdate } from '../api/types'
import { createUser, deleteUser, listUsers, updateUser } from '../api/users'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import Modal from '../components/Modal.vue'
import PageHeader from '../components/PageHeader.vue'
import { formatTime, userStatusLabel } from '../utils/format'

const limit = 10
const offset = ref(0)
const users = ref<User[]>([])
const loading = ref(false)
const error = ref('')
const editorOpen = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const formError = ref('')
const pendingDelete = ref<User | null>(null)
const deleting = ref(false)

const form = reactive({
  username: '',
  email: '',
  full_name: '',
  password: '',
})

const page = computed(() => offset.value / limit + 1)
const hasNext = computed(() => users.value.length === limit)
const editorTitle = computed(() => (editingId.value == null ? '新建用户' : '编辑用户'))

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await listUsers(offset.value, limit)
    users.value = Array.isArray(data) ? data : []
  } catch (err) {
    users.value = []
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.username = ''
  form.email = ''
  form.full_name = ''
  form.password = ''
  formError.value = ''
}

function openCreate() {
  editingId.value = null
  resetForm()
  editorOpen.value = true
}

function openEdit(user: User) {
  editingId.value = user.id
  form.username = user.username
  form.email = user.email
  form.full_name = user.full_name ?? ''
  form.password = ''
  formError.value = ''
  editorOpen.value = true
}

async function save() {
  formError.value = ''
  const username = form.username.trim()
  const email = form.email.trim()
  if (username.length < 3) {
    formError.value = '用户名至少 3 位'
    return
  }
  if (!email) {
    formError.value = '请填写邮箱'
    return
  }
  if (editingId.value == null && form.password.length < 6) {
    formError.value = '密码至少 6 位'
    return
  }
  if (form.password && form.password.length < 6) {
    formError.value = '密码至少 6 位'
    return
  }

  saving.value = true
  try {
    if (editingId.value == null) {
      await createUser({
        username,
        email,
        password: form.password,
        full_name: form.full_name.trim() || null,
      })
    } else {
      const body: UserUpdate = {
        username,
        email,
        full_name: form.full_name.trim() || null,
      }
      if (form.password) body.password = form.password
      await updateUser(editingId.value, body)
    }
    editorOpen.value = false
    await load()
  } catch (err) {
    formError.value = errorMessage(err)
  } finally {
    saving.value = false
  }
}

async function confirmDelete() {
  if (!pendingDelete.value) return
  deleting.value = true
  try {
    await deleteUser(pendingDelete.value.id)
    pendingDelete.value = null
    if (users.value.length === 1 && offset.value > 0) offset.value -= limit
    await load()
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    deleting.value = false
  }
}

function prevPage() {
  if (offset.value === 0) return
  offset.value -= limit
  load()
}

function nextPage() {
  if (!hasNext.value) return
  offset.value += limit
  load()
}

onMounted(load)
</script>

<template>
  <section class="page">
    <PageHeader title="用户" description="查看、新建和修改账号。密码不会显示在列表里。">
      <button class="btn btn--primary" type="button" @click="openCreate">新建用户</button>
    </PageHeader>

    <p v-if="error" class="banner">{{ error }}</p>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>用户名</th>
            <th>邮箱</th>
            <th>姓名</th>
            <th>状态</th>
            <th>创建时间</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="6" class="muted">加载中…</td>
          </tr>
          <tr v-else-if="users.length === 0">
            <td colspan="6" class="muted">还没有用户</td>
          </tr>
          <template v-else>
          <tr v-for="user in users" :key="user.id">
            <td>{{ user.username }}</td>
            <td>{{ user.email }}</td>
            <td>{{ user.full_name || '—' }}</td>
            <td><span class="badge">{{ userStatusLabel(user.status) }}</span></td>
            <td>{{ formatTime(user.created_at) }}</td>
            <td class="row-actions">
              <button class="btn btn--ghost" type="button" @click="openEdit(user)">编辑</button>
              <button class="btn btn--ghost" type="button" @click="pendingDelete = user">删除</button>
            </td>
          </tr>
          </template>
        </tbody>
      </table>
    </div>

    <footer class="pager">
      <button class="btn btn--ghost" type="button" :disabled="offset === 0 || loading" @click="prevPage">
        上一页
      </button>
      <span>第 {{ page }} 页</span>
      <button class="btn btn--ghost" type="button" :disabled="!hasNext || loading" @click="nextPage">
        下一页
      </button>
    </footer>

    <Modal v-model="editorOpen" :title="editorTitle">
      <form id="user-form" class="form" @submit.prevent="save">
        <label class="field">
          <span>用户名</span>
          <input v-model="form.username" />
        </label>
        <label class="field">
          <span>邮箱</span>
          <input v-model="form.email" type="email" />
        </label>
        <label class="field">
          <span>姓名</span>
          <input v-model="form.full_name" placeholder="可选" />
        </label>
        <label class="field">
          <span>密码</span>
          <input
            v-model="form.password"
            type="password"
            :placeholder="editingId == null ? '至少 6 位' : '留空则不修改'"
          />
        </label>
        <p v-if="formError" class="form-error">{{ formError }}</p>
      </form>
      <template #footer>
        <button class="btn btn--ghost" type="button" @click="editorOpen = false">取消</button>
        <button class="btn btn--primary" type="submit" form="user-form" :disabled="saving">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </template>
    </Modal>

    <ConfirmDialog
      :open="pendingDelete != null"
      title="删除用户"
      :message="pendingDelete ? `确定删除 ${pendingDelete.username}？此操作不能撤销。` : ''"
      :pending="deleting"
      @cancel="pendingDelete = null"
      @confirm="confirmDelete"
    />
  </section>
</template>
