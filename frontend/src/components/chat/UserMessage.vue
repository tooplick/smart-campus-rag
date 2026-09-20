<script setup lang="ts">
defineProps<{
  content: string
}>()
</script>

<template>
  <div class="flex justify-end mb-4">
    <div class="max-w-[70%]">
      <div class="bg-primary text-primary-foreground px-4 py-2.5 rounded-2xl rounded-br-md text-sm whitespace-pre-wrap">
        {{ content }}
      </div>
    </div>
  </div>
</template>
