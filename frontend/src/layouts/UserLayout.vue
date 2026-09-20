<script setup lang="ts">
import AppHeader from '@/components/common/AppHeader.vue'
</script>

<template>
  <div class="flex h-screen flex-col">
    <AppHeader />
    <main class="flex-1 overflow-hidden">
      <router-view />
    </main>
  </div>
</template>
