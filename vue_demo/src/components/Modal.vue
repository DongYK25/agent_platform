<script setup lang="ts">
defineProps<{ title: string }>()
const open = defineModel<boolean>({ required: true })
</script>

<template>
  <div v-if="open" class="modal-root" @click.self="open = false">
    <div class="modal" role="dialog" aria-modal="true" :aria-label="title">
      <header class="modal__head">
        <h2>{{ title }}</h2>
        <button class="icon-btn" type="button" aria-label="关闭" @click="open = false">×</button>
      </header>
      <div class="modal__body">
        <slot />
      </div>
      <footer v-if="$slots.footer" class="modal__foot">
        <slot name="footer" />
      </footer>
    </div>
  </div>
</template>
