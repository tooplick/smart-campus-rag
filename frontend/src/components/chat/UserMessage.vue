<script setup lang="ts">
defineProps<{ content: string }>()
</script>

<template>
  <div class="flex justify-end">
    <div class="max-w-[80%] whitespace-pre-wrap rounded-2xl bg-primary px-4 py-2 text-sm text-primary-foreground">
      {{ content }}
    </div>
  </div>
</template>
