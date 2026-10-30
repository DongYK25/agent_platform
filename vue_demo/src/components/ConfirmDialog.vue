<script setup lang="ts">
defineProps<{
  open: boolean
  title: string
  message: string
  pending?: boolean
}>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<template>
  <div v-if="open" class="modal-root">
    <div class="modal modal--narrow" role="dialog" aria-modal="true" :aria-label="title">
      <header class="modal__head">
        <h2>{{ title }}</h2>
      </header>
      <div class="modal__body">
        <p>{{ message }}</p>
      </div>
      <footer class="modal__foot">
        <button class="btn btn--ghost" type="button" :disabled="pending" @click="emit('cancel')">
          取消
        </button>
        <button class="btn btn--danger" type="button" :disabled="pending" @click="emit('confirm')">
          {{ pending ? '删除中…' : '删除' }}
        </button>
      </footer>
    </div>
  </div>
</template>
