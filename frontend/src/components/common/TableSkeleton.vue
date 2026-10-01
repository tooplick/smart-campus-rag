<script setup lang="ts">
// 表格加载骨架:表头 + 若干行占位,行列数参数化以适配不同表格
import { Skeleton } from '@/components/ui/skeleton'

const props = withDefaults(defineProps<{ rows?: number; cols?: number }>(), { rows: 5, cols: 6 })
</script>

<template>
  <div class="space-y-3">
    <div class="flex gap-4">
      <Skeleton v-for="c in props.cols" :key="`h-${c}`" class="h-4 flex-1" />
    </div>
    <div v-for="r in props.rows" :key="r" class="flex gap-4">
      <Skeleton v-for="c in props.cols" :key="`${r}-${c}`" class="h-4 flex-1" />
    </div>
  </div>
</template>
