<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { errorMessage } from '../api/http'
import type { WorkOrder } from '../api/types'
import {
  createWorkOrder,
  deleteWorkOrder,
  getWorkOrder,
  listWorkOrders,
  updateWorkOrder,
} from '../api/workOrders'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import Modal from '../components/Modal.vue'
import PageHeader from '../components/PageHeader.vue'
import { labelOf, priorities, workOrderStatuses } from '../constants'
import { formatTime } from '../utils/format'

const limit = 10
const offset = ref(0)
const orders = ref<WorkOrder[]>([])
const loading = ref(false)
const error = ref('')
const editorOpen = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const formError = ref('')
const pendingDelete = ref<WorkOrder | null>(null)
const deleting = ref(false)

const form = reactive({
  title: '',
  content: '',
  status: 'pending',
  order_type: '',
  priority: 'medium',
  handler_id: '',
  remark: '',
})

const page = computed(() => offset.value / limit + 1)
const hasNext = computed(() => orders.value.length === limit)
const editorTitle = computed(() => (editingId.value == null ? '新建工单' : '编辑工单'))

function badgeClass(status?: string | null) {
  if (status === 'pending' || status === 'processing' || status === 'done') {
    return `badge badge--${status}`
  }
  return 'badge'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await listWorkOrders(offset.value, limit)
    orders.value = Array.isArray(data) ? data : []
  } catch (err) {
    orders.value = []
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.title = ''
  form.content = ''
  form.status = 'pending'
  form.order_type = ''
  form.priority = 'medium'
  form.handler_id = ''
  form.remark = ''
  formError.value = ''
}

function openCreate() {
  editingId.value = null
  resetForm()
  editorOpen.value = true
}

async function openEdit(order: WorkOrder) {
  editingId.value = order.id
  resetForm()
  editorOpen.value = true
  try {
    const detail = await getWorkOrder(order.id)
    form.title = detail.title ?? ''
    form.content = detail.content ?? ''
    form.status = detail.status || 'pending'
    form.order_type = detail.order_type ?? ''
    form.priority = detail.priority || 'medium'
    form.handler_id = detail.handler_id == null ? '' : String(detail.handler_id)
    form.remark = detail.remark ?? ''
  } catch (err) {
    formError.value = errorMessage(err)
  }
}

function handlerId() {
  const text = form.handler_id.trim()
  if (!text) return null
  const value = Number(text)
  return Number.isInteger(value) ? value : Number.NaN
}

async function save() {
  formError.value = ''
  const title = form.title.trim()
  if (!title) {
    formError.value = '请填写标题'
    return
  }
  const handler = handlerId()
  if (Number.isNaN(handler)) {
    formError.value = '处理人需要是整数'
    return
  }

  const payload = {
    title,
    content: form.content.trim() || null,
    status: form.status,
    order_type: form.order_type.trim() || null,
    priority: form.priority || null,
    handler_id: handler,
    remark: form.remark.trim() || null,
  }

  saving.value = true
  try {
    if (editingId.value == null) {
      await createWorkOrder(payload)
    } else {
      await updateWorkOrder(editingId.value, { id: editingId.value, ...payload })
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
    await deleteWorkOrder(pendingDelete.value.id)
    pendingDelete.value = null
    if (orders.value.length === 1 && offset.value > 0) offset.value -= limit
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
    <PageHeader title="工单" description="列表只展示摘要。编辑时会再读取内容、备注和处理人。">
      <button class="btn btn--primary" type="button" @click="openCreate">新建工单</button>
    </PageHeader>

    <p v-if="error" class="banner">{{ error }}</p>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>标题</th>
            <th>状态</th>
            <th>优先级</th>
            <th>类型</th>
            <th>创建人</th>
            <th>处理人</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7" class="muted">加载中…</td>
          </tr>
          <tr v-else-if="orders.length === 0">
            <td colspan="7" class="muted">还没有工单</td>
          </tr>
          <template v-else>
          <tr v-for="order in orders" :key="order.id">
            <td>
              <strong>{{ order.title }}</strong>
              <small v-if="order.created_at">{{ formatTime(order.created_at) }}</small>
            </td>
            <td><span :class="badgeClass(order.status)">{{ labelOf(workOrderStatuses, order.status) }}</span></td>
            <td>{{ labelOf(priorities, order.priority) }}</td>
            <td>{{ order.order_type || '—' }}</td>
            <td>{{ order.creator_id ?? '—' }}</td>
            <td>{{ order.handler_id ?? '—' }}</td>
            <td class="row-actions">
              <button class="btn btn--ghost" type="button" @click="openEdit(order)">编辑</button>
              <button class="btn btn--ghost" type="button" @click="pendingDelete = order">删除</button>
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
      <form id="order-form" class="form form--grid" @submit.prevent="save">
        <label class="field field--wide">
          <span>标题</span>
          <input v-model="form.title" />
        </label>
        <label class="field">
          <span>状态</span>
          <select v-model="form.status">
            <option v-for="item in workOrderStatuses" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
        </label>
        <label class="field">
          <span>优先级</span>
          <select v-model="form.priority">
            <option v-for="item in priorities" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
        </label>
        <label class="field">
          <span>类型</span>
          <input v-model="form.order_type" placeholder="例如：故障、咨询" />
        </label>
        <label class="field">
          <span>处理人 ID</span>
          <input v-model="form.handler_id" inputmode="numeric" placeholder="可选" />
        </label>
        <label class="field field--wide">
          <span>内容</span>
          <textarea v-model="form.content" rows="4" />
        </label>
        <label class="field field--wide">
          <span>备注</span>
          <textarea v-model="form.remark" rows="2" />
        </label>
        <p v-if="formError" class="form-error field--wide">{{ formError }}</p>
      </form>
      <template #footer>
        <button class="btn btn--ghost" type="button" @click="editorOpen = false">取消</button>
        <button class="btn btn--primary" type="submit" form="order-form" :disabled="saving">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </template>
    </Modal>

    <ConfirmDialog
      :open="pendingDelete != null"
      title="删除工单"
      :message="pendingDelete ? `确定删除「${pendingDelete.title}」？` : ''"
      :pending="deleting"
      @cancel="pendingDelete = null"
      @confirm="confirmDelete"
    />
  </section>
</template>
