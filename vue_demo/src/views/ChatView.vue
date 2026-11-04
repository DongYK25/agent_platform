<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import {
  createSession,
  deleteSession,
  getChatHistory,
  listSessions,
  renameSession,
  sendChat,
  type ChatSession,
} from '../api/agent'
import { errorMessage } from '../api/http'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import Modal from '../components/Modal.vue'

interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
}

const sessions = ref<ChatSession[]>([])
const activeId = ref<string | null>(null)
const transcripts = ref<Record<string, ChatMessage[]>>({})
const loadedIds = new Set<string>()
const draft = ref('')
const pending = ref(false)
const loadingList = ref(false)
const loadingHistoryId = ref<string | null>(null)
const creating = ref(false)
const error = ref('')
const scroller = ref<HTMLElement | null>(null)
const renameOpen = ref(false)
const renameTitle = ref('')
const renamingId = ref<string | null>(null)
const savingTitle = ref(false)
const renameError = ref('')
const pendingDelete = ref<ChatSession | null>(null)
const deleting = ref(false)
let seed = 0

const messages = computed(() =>
  activeId.value ? transcripts.value[activeId.value] ?? [] : [],
)
const activeTitle = computed(
  () => sessions.value.find((item) => item.id === activeId.value)?.title || '对话',
)
const loadingHistory = computed(() => loadingHistoryId.value === activeId.value)
const lastUserText = computed(() => {
  const list = messages.value
  for (let index = list.length - 1; index >= 0; index -= 1) {
    const text = list[index].content.trim()
    if (list[index].role === 'user' && text) return text
  }
  return ''
})

watch(
  messages,
  async () => {
    await nextTickScroll()
  },
  { deep: true },
)

async function nextTickScroll() {
  await nextTick()
  const el = scroller.value
  if (el) el.scrollTop = el.scrollHeight
}

function nextId() {
  seed += 1
  return seed
}

async function loadSessions() {
  loadingList.value = true
  error.value = ''
  try {
    const data = await listSessions()
    sessions.value = Array.isArray(data) ? data : []
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loadingList.value = false
  }
}

async function selectSession(id: string) {
  activeId.value = id
  error.value = ''
  if (loadedIds.has(id) || loadingHistoryId.value === id) return
  loadingHistoryId.value = id
  try {
    const history = await getChatHistory(id)
    transcripts.value[id] = (Array.isArray(history) ? history : []).map((item) => ({
      id: nextId(),
      role: item.role === 'user' ? 'user' : 'assistant',
      content: item.content ?? '',
    }))
    loadedIds.add(id)
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    if (loadingHistoryId.value === id) loadingHistoryId.value = null
  }
}

async function create() {
  if (creating.value) return
  creating.value = true
  error.value = ''
  try {
    const row = await createSession()
    sessions.value = [row, ...sessions.value.filter((item) => item.id !== row.id)]
    transcripts.value[row.id] = []
    loadedIds.add(row.id)
    activeId.value = row.id
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    creating.value = false
  }
}

function openRename(item: ChatSession) {
  renamingId.value = item.id
  renameTitle.value = item.title || ''
  renameError.value = ''
  renameOpen.value = true
}

async function saveRename() {
  const id = renamingId.value
  const title = renameTitle.value.trim()
  if (!id) return
  if (!title) {
    renameError.value = '标题不能为空'
    return
  }
  savingTitle.value = true
  renameError.value = ''
  try {
    const row = await renameSession(id, title)
    const current = sessions.value.find((item) => item.id === id)
    if (current) current.title = row.title || title
    renameOpen.value = false
  } catch (err) {
    renameError.value = errorMessage(err)
  } finally {
    savingTitle.value = false
  }
}

async function confirmDelete() {
  const target = pendingDelete.value
  if (!target) return
  deleting.value = true
  try {
    await deleteSession(target.id)
    sessions.value = sessions.value.filter((item) => item.id !== target.id)
    delete transcripts.value[target.id]
    loadedIds.delete(target.id)
    if (activeId.value === target.id) activeId.value = null
    pendingDelete.value = null
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    deleting.value = false
  }
}

async function sendText(text: string) {
  const sessionUid = activeId.value
  if (!sessionUid || pending.value) return
  error.value = ''
  const bucket = transcripts.value[sessionUid] ?? []
  transcripts.value[sessionUid] = [...bucket, { id: nextId(), role: 'user', content: text }]
  pending.value = true
  try {
    const reply = await sendChat(text, sessionUid)
    const current = transcripts.value[sessionUid] ?? []
    transcripts.value[sessionUid] = [
      ...current,
      { id: nextId(), role: 'assistant', content: reply || '（空回复）' },
    ]
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    pending.value = false
  }
}

async function submit() {
  const text = draft.value.trim()
  if (!text) return
  draft.value = ''
  await sendText(text)
}

async function resend() {
  if (!lastUserText.value) return
  await sendText(lastUserText.value)
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    submit()
  }
}

onMounted(loadSessions)
</script>

<template>
  <section class="chat-page">
    <aside class="sessions">
      <div class="sessions__head">
        <strong>对话窗口</strong>
        <button class="btn btn--primary" type="button" :disabled="creating" @click="create">
          {{ creating ? '创建中…' : '新建' }}
        </button>
      </div>
      <p v-if="loadingList" class="sessions__hint">加载中…</p>
      <p v-else-if="sessions.length === 0" class="sessions__hint">还没有对话</p>
      <ul v-else class="sessions__list">
        <li
          v-for="item in sessions"
          :key="item.id"
          class="session-item"
          :class="{ 'is-active': item.id === activeId }"
        >
          <button class="session-item__open" type="button" @click="selectSession(item.id)">
            {{ item.title || '未命名' }}
          </button>
          <div class="session-item__ops">
            <button type="button" @click="openRename(item)">改名</button>
            <button type="button" @click="pendingDelete = item">删除</button>
          </div>
        </li>
      </ul>
    </aside>

    <div class="chat">
      <header class="chat__head">
        <div>
          <h1>{{ activeId ? activeTitle : '对话' }}</h1>
          <p>点开一个窗口会查询一次历史。重新发送会把你最后一条消息再提交一次。</p>
        </div>
      </header>

      <div ref="scroller" class="chat__log">
        <div v-if="!activeId" class="chat__empty">
          <strong>先选择或新建一个对话</strong>
          <span>新建后的名称会按对话1、对话2自动排列。</span>
        </div>
        <div v-else-if="loadingHistory" class="chat__empty">
          <strong>正在读取记录…</strong>
        </div>
        <div v-else-if="messages.length === 0" class="chat__empty">
          <strong>这个窗口还没有消息</strong>
          <span>写一句问候，开始这次对话。</span>
        </div>
        <article
          v-for="message in messages"
          :key="message.id"
          class="bubble"
          :class="message.role === 'user' ? 'bubble--user' : 'bubble--assistant'"
        >
          <span>{{ message.role === 'user' ? '我' : 'Agent' }}</span>
          <p>{{ message.content }}</p>
        </article>
        <p v-if="pending" class="bubble bubble--assistant bubble--pending">正在回复…</p>
      </div>

      <form class="composer" @submit.prevent="submit">
        <p v-if="error" class="form-error">{{ error }}</p>
        <div class="composer__row">
          <textarea
            v-model="draft"
            rows="2"
            :disabled="!activeId || pending"
            placeholder="输入消息，Enter 发送，Shift + Enter 换行"
            @keydown="onKeydown"
          />
          <button
            class="btn btn--ghost"
            type="button"
            :disabled="!activeId || pending || !lastUserText"
            @click="resend"
          >
            重新发送
          </button>
          <button class="btn btn--primary" type="submit" :disabled="!activeId || pending || !draft.trim()">
            发送
          </button>
        </div>
      </form>
    </div>

    <Modal v-model="renameOpen" title="修改名称">
      <form id="rename-form" class="form" @submit.prevent="saveRename">
        <label class="field">
          <span>标题</span>
          <input v-model="renameTitle" />
        </label>
        <p v-if="renameError" class="form-error">{{ renameError }}</p>
      </form>
      <template #footer>
        <button class="btn btn--ghost" type="button" @click="renameOpen = false">取消</button>
        <button class="btn btn--primary" type="submit" form="rename-form" :disabled="savingTitle">
          {{ savingTitle ? '保存中…' : '保存' }}
        </button>
      </template>
    </Modal>

    <ConfirmDialog
      :open="pendingDelete != null"
      title="删除对话"
      :message="pendingDelete ? `确定删除「${pendingDelete.title || '未命名'}」？记录会一起删除。` : ''"
      :pending="deleting"
      @cancel="pendingDelete = null"
      @confirm="confirmDelete"
    />
  </section>
</template>
