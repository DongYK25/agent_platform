<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { sendKnowledgeAgentMessage } from '../api/agent'
import { errorMessage } from '../api/http'

interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
}

const suggestions = [
  '公司的年假和调休制度是什么？',
  '新员工入职需要完成哪些事项？',
  '如何申请办公设备或软件权限？',
  '差旅费用的报销标准是什么？',
]

const sessionUid = ref(createSessionUid())
const messages = ref<ChatMessage[]>([])
const draft = ref('')
const pending = ref(false)
const error = ref('')
const scroller = ref<HTMLElement | null>(null)
let messageSeed = 0

const shortSessionUid = computed(() => sessionUid.value.slice(0, 8))

watch(
  messages,
  async () => {
    await nextTick()
    const element = scroller.value
    if (element) element.scrollTop = element.scrollHeight
  },
  { deep: true },
)

function createSessionUid() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (character) => {
    const random = Math.floor(Math.random() * 16)
    const value = character === 'x' ? random : (random & 0x3) | 0x8
    return value.toString(16)
  })
}

function nextMessageId() {
  messageSeed += 1
  return messageSeed
}

function newConversation() {
  if (pending.value) return
  sessionUid.value = createSessionUid()
  messages.value = []
  draft.value = ''
  error.value = ''
}

async function sendText(text: string) {
  const content = text.trim()
  if (!content || pending.value) return

  const currentSessionUid = sessionUid.value
  messages.value.push({ id: nextMessageId(), role: 'user', content })
  pending.value = true
  error.value = ''

  try {
    const reply = await sendKnowledgeAgentMessage(content, currentSessionUid)
    if (sessionUid.value !== currentSessionUid) return
    messages.value.push({
      id: nextMessageId(),
      role: 'assistant',
      content: reply || '暂时没有查询到相关内容。',
    })
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    if (sessionUid.value === currentSessionUid) pending.value = false
  }
}

async function submit() {
  const content = draft.value.trim()
  if (!content) return
  draft.value = ''
  await sendText(content)
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    submit()
  }
}
</script>

<template>
  <section class="knowledge-agent">
    <header class="knowledge-agent__head">
      <div class="agent-identity">
        <span class="agent-identity__mark" aria-hidden="true">知</span>
        <div>
          <div class="agent-identity__title">
            <h1>企业知识库助手</h1>
            <span class="online-dot">在线</span>
          </div>
          <p>查询公司制度、业务流程和内部办事指南</p>
        </div>
      </div>
      <div class="session-actions">
        <span class="session-code">会话 {{ shortSessionUid }}</span>
        <button class="btn btn--primary" type="button" :disabled="pending" @click="newConversation">
          ＋ 新对话
        </button>
      </div>
    </header>

    <div ref="scroller" class="knowledge-agent__log">
      <div v-if="messages.length === 0" class="welcome">
        <span class="welcome__icon" aria-hidden="true">知</span>
        <h2>你好，我是企业知识库助手</h2>
        <p>你可以向我咨询公司制度、工作流程、系统使用等内部知识。</p>
        <div class="suggestions">
          <button
            v-for="suggestion in suggestions"
            :key="suggestion"
            type="button"
            :disabled="pending"
            @click="sendText(suggestion)"
          >
            <span>{{ suggestion }}</span>
            <b aria-hidden="true">→</b>
          </button>
        </div>
        <small>每次点击“新对话”都会创建独立会话，上下文不会带入下一次对话。</small>
      </div>

      <div v-else class="message-list">
        <article
          v-for="message in messages"
          :key="message.id"
          class="agent-message"
          :class="`agent-message--${message.role}`"
        >
          <span class="agent-message__avatar">{{ message.role === 'user' ? '我' : '知' }}</span>
          <div>
            <strong>{{ message.role === 'user' ? '我' : '知识库助手' }}</strong>
            <p>{{ message.content }}</p>
          </div>
        </article>
        <article v-if="pending" class="agent-message agent-message--assistant">
          <span class="agent-message__avatar">知</span>
          <div>
            <strong>知识库助手</strong>
            <p class="typing"><i></i><i></i><i></i><span>正在查询知识库…</span></p>
          </div>
        </article>
      </div>
    </div>

    <form class="agent-composer" @submit.prevent="submit">
      <p v-if="error" class="form-error">{{ error }}</p>
      <div class="agent-composer__box">
        <textarea
          v-model="draft"
          rows="2"
          :disabled="pending"
          placeholder="请输入你想了解的公司问题…"
          aria-label="消息内容"
          @keydown="onKeydown"
        />
        <button class="send-button" type="submit" :disabled="pending || !draft.trim()">
          {{ pending ? '查询中' : '发送' }}
        </button>
      </div>
      <small>内容由企业知识库生成，请结合最新制度文件核实重要信息。</small>
    </form>
  </section>
</template>

<style scoped>
.knowledge-agent {
  display: flex;
  flex: 1;
  flex-direction: column;
  width: 100%;
  min-height: 0;
  background:
    radial-gradient(circle at 50% 0, rgba(15, 107, 98, 0.08), transparent 24rem),
    #f8f7f3;
}

.knowledge-agent__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--line);
  background: rgba(255, 253, 249, 0.88);
  backdrop-filter: blur(12px);
}

.agent-identity,
.agent-identity__title,
.session-actions {
  display: flex;
  align-items: center;
}

.agent-identity { gap: 0.85rem; }
.agent-identity__title { gap: 0.65rem; }
.agent-identity__title h1 { margin: 0; font-size: 1.25rem; font-weight: 600; }
.agent-identity p { margin-top: 0.15rem; color: var(--muted); font-size: 0.86rem; }

.agent-identity__mark,
.welcome__icon {
  display: grid;
  place-items: center;
  color: white;
  background: linear-gradient(145deg, #168477, var(--accent-strong));
  box-shadow: 0 8px 20px rgba(15, 107, 98, 0.2);
}

.agent-identity__mark { width: 2.7rem; height: 2.7rem; border-radius: 13px; font-weight: 600; }
.online-dot { color: var(--accent); font-size: 0.75rem; }
.online-dot::before { content: ''; display: inline-block; width: 0.45rem; height: 0.45rem; margin-right: 0.3rem; border-radius: 50%; background: #2eaa79; }
.session-actions { gap: 0.75rem; }
.session-code { color: var(--muted); font-size: 0.78rem; font-variant-numeric: tabular-nums; }

.knowledge-agent__log { flex: 1; min-height: 0; overflow: auto; padding: 2rem 1.5rem; }

.welcome {
  width: min(700px, 100%);
  min-height: 100%;
  margin: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.welcome__icon { width: 4rem; height: 4rem; margin-bottom: 1.1rem; border-radius: 20px; font-size: 1.35rem; font-weight: 600; }
.welcome h2 { font-size: clamp(1.55rem, 3vw, 2rem); font-weight: 550; }
.welcome > p { margin-top: 0.55rem; color: var(--muted); }
.welcome > small { margin-top: 1.1rem; color: var(--muted); }

.suggestions {
  width: 100%;
  margin-top: 1.8rem;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.suggestions button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.9rem 1rem;
  border: 1px solid var(--line);
  border-radius: 14px;
  color: var(--ink);
  background: rgba(255, 255, 255, 0.78);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.16s, transform 0.16s, box-shadow 0.16s;
}

.suggestions button:hover:not(:disabled) { transform: translateY(-2px); border-color: rgba(15, 107, 98, 0.45); box-shadow: var(--shadow); }
.suggestions button:disabled { cursor: not-allowed; opacity: 0.55; }
.suggestions b { color: var(--accent); font-size: 1.1rem; font-weight: 400; }

.message-list { width: min(820px, 100%); margin: 0 auto; display: flex; flex-direction: column; gap: 1.25rem; }
.agent-message { display: flex; align-items: flex-start; gap: 0.75rem; }
.agent-message--user { flex-direction: row-reverse; }
.agent-message > div { max-width: min(660px, 82%); }
.agent-message strong { display: block; margin-bottom: 0.3rem; color: var(--muted); font-size: 0.76rem; font-weight: 500; }
.agent-message--user strong { text-align: right; }
.agent-message p { margin: 0; padding: 0.85rem 1rem; border: 1px solid var(--line); border-radius: 4px 16px 16px; background: white; box-shadow: 0 5px 18px rgba(48, 36, 22, 0.04); white-space: pre-wrap; overflow-wrap: anywhere; }
.agent-message--user p { border: 0; border-radius: 16px 4px 16px 16px; color: white; background: var(--accent); }
.agent-message__avatar { flex: 0 0 auto; display: grid; place-items: center; width: 2rem; height: 2rem; border-radius: 10px; color: white; background: var(--accent); font-size: 0.78rem; }
.agent-message--user .agent-message__avatar { color: var(--ink); background: #eadfcf; }

.typing { display: flex; align-items: center; gap: 0.28rem; color: var(--muted); }
.typing i { width: 0.35rem; height: 0.35rem; border-radius: 50%; background: var(--accent); animation: pulse 1.2s infinite ease-in-out; }
.typing i:nth-child(2) { animation-delay: 0.15s; }
.typing i:nth-child(3) { animation-delay: 0.3s; }
.typing span { margin-left: 0.35rem; font-style: normal; }

.agent-composer { width: min(870px, calc(100% - 2rem)); margin: 0 auto; padding: 0 0 1.25rem; }
.agent-composer .form-error { margin-bottom: 0.45rem; }
.agent-composer__box { display: flex; align-items: flex-end; gap: 0.75rem; padding: 0.65rem; border: 1px solid var(--line); border-radius: 18px; background: white; box-shadow: 0 12px 32px rgba(48, 36, 22, 0.08); }
.agent-composer textarea { flex: 1; min-height: 3rem; max-height: 9rem; padding: 0.45rem 0.55rem; border: 0; outline: 0; resize: vertical; background: transparent; }
.agent-composer > small { display: block; margin-top: 0.5rem; color: var(--muted); text-align: center; font-size: 0.72rem; }
.send-button { flex: 0 0 auto; min-width: 4.6rem; padding: 0.65rem 1rem; border: 0; border-radius: 12px; color: white; background: var(--accent); cursor: pointer; }
.send-button:hover:not(:disabled) { background: var(--accent-strong); }
.send-button:disabled { cursor: not-allowed; opacity: 0.5; }

@keyframes pulse {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-3px); opacity: 1; }
}

@media (max-width: 700px) {
  .knowledge-agent__head { align-items: flex-start; padding: 0.85rem 1rem; }
  .agent-identity p, .session-code { display: none; }
  .session-actions .btn { padding-inline: 0.8rem; }
  .knowledge-agent__log { padding: 1.2rem 1rem; }
  .suggestions { grid-template-columns: 1fr; }
  .agent-message > div { max-width: 86%; }
  .agent-composer { width: calc(100% - 1.25rem); padding-bottom: 0.65rem; }
}
</style>
