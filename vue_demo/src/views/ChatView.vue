<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { sendChat } from '../api/agent'
import { errorMessage } from '../api/http'
import { messages, nextChatId } from '../chatState'

const draft = ref('')
const pending = ref(false)
const error = ref('')
const scroller = ref<HTMLElement | null>(null)

watch(
  messages,
  async () => {
    await nextTick()
    const el = scroller.value
    if (el) el.scrollTop = el.scrollHeight
  },
  { deep: true },
)

async function submit() {
  const text = draft.value.trim()
  if (!text || pending.value) return
  error.value = ''
  draft.value = ''
  messages.value.push({ id: nextChatId(), role: 'user', content: text })
  pending.value = true
  try {
    const reply = await sendChat(text)
    messages.value.push({
      id: nextChatId(),
      role: 'assistant',
      content: reply || '（空回复）',
    })
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    pending.value = false
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    submit()
  }
}
</script>

<template>
  <section class="chat">
    <header class="chat__head">
      <div>
        <h1>对话</h1>
        <p>发送一条消息。当前服务进程会记住上下文，刷新页面后界面记录会清空。</p>
      </div>
    </header>

    <div ref="scroller" class="chat__log">
      <div v-if="messages.length === 0" class="chat__empty">
        <strong>从一句问候开始</strong>
        <span>例如：帮我总结今天要处理的工单类型。</span>
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
          placeholder="输入消息，Enter 发送，Shift + Enter 换行"
          @keydown="onKeydown"
        />
        <button class="btn btn--primary" type="submit" :disabled="pending || !draft.trim()">
          发送
        </button>
      </div>
    </form>
  </section>
</template>
