<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{ icon?: Component; title: string; description?: string }>()
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-2 py-12 text-center">
    <component :is="icon" v-if="icon" class="h-10 w-10 text-muted-foreground" />
    <p class="text-sm font-medium">{{ title }}</p>
    <p v-if="description" class="text-sm text-muted-foreground">{{ description }}</p>
  </div>
</template>
