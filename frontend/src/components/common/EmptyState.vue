<script setup lang="ts">
// 空态/错误态通用占位:variant="error" 时红色图标;action 插槽可放「重试」等按钮
import type { Component } from 'vue'

defineProps<{
  icon?: Component
  title: string
  description?: string
  variant?: 'default' | 'error'
}>()
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-2 py-12 text-center">
    <component
      :is="icon" v-if="icon" class="h-10 w-10"
      :class="variant === 'error' ? 'text-destructive' : 'text-muted-foreground'"
    />
    <p class="text-sm font-medium">{{ title }}</p>
    <p v-if="description" class="max-w-md text-sm text-muted-foreground">{{ description }}</p>
    <div v-if="$slots.action" class="mt-2">
      <slot name="action" />
    </div>
  </div>
</template>
