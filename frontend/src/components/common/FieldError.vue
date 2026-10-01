<script setup lang="ts">
// 字段级内联错误:无错误时渲染空占位行,避免出现/消失引起表单跳版
defineProps<{ message?: string }>()
</script>

<template>
  <p class="min-h-4 text-xs text-destructive">{{ message ?? '' }}</p>
</template>
