<script setup lang="ts">
import { Toaster } from '@/components/ui/sonner'
import AppShell from '@/components/shell/AppShell.vue'
</script>

<template>
  <Toaster position="top-center" />
  <!-- 所有页面(含 Login/Initialize)共享统一壳层:顶栏 + 侧栏 + 内容区(内含 router-view) -->
  <AppShell />
</template>
