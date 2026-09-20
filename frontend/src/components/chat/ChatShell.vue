<script setup lang="ts">
import ConversationSidebar from './ConversationSidebar.vue'

const emit = defineEmits<{
  'new-conversation': []
}>()
</script>

<template>
  <div class="flex h-full">
    <ConversationSidebar @new-conversation="emit('new-conversation')" />
    <div class="flex-1 flex flex-col overflow-hidden">
      <slot />
    </div>
  </div>
</template>
