<script setup lang="ts">
// 管理端仪表盘:统计卡片 + 问答趋势 / 文档状态 / 知识库分布三张图表
import { computed, onMounted } from 'vue'
import { Database, FileText, Layers, MessageSquare } from '@lucide/vue'
import type { EChartsOption } from 'echarts'
import { useAdminStore } from '@/stores/admin'
import Chart from '@/components/admin/Chart.vue'

const admin = useAdminStore()
onMounted(() => admin.loadDashboard())

/** 顶部统计卡片数据 */
const stats = computed(() => {
  const s = admin.dashboard?.statistics
  return [
    { label: '知识库数量', value: s?.knowledge_base_count ?? 0, icon: Database },
    { label: '文档数量', value: s?.document_count ?? 0, icon: FileText },
    { label: 'Chunk 数量', value: s?.chunk_count ?? 0, icon: Layers },
    { label: '问答次数', value: s?.qa_count ?? 0, icon: MessageSquare },
  ]
})

/** 问答趋势(近 7 天)折线图 */
const trendOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 16, top: 24, bottom: 32 },
  xAxis: { type: 'category', data: admin.dashboard?.qa_trend.map((t) => t.date) ?? [] },
  yAxis: { type: 'value', minInterval: 1 },
  series: [{ type: 'line', smooth: true, areaStyle: { opacity: 0.15 }, data: admin.dashboard?.qa_trend.map((t) => t.count) ?? [] }],
}))

/** 文档处理状态环形图 */
const statusOption = computed<EChartsOption>(() => {
  const d = admin.dashboard?.document_status
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      data: [
        { name: '待处理', value: d?.pending ?? 0 },
        { name: '处理中', value: d?.processing ?? 0 },
        { name: '已完成', value: d?.completed ?? 0 },
        { name: '失败', value: d?.failed ?? 0 },
      ],
    }],
  }
})

/** 知识库文档分布横向柱状图 */
const distOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 100, right: 16, top: 16, bottom: 32 },
  xAxis: { type: 'value', minInterval: 1 },
  yAxis: {
    type: 'category',
    data: admin.dashboard?.knowledge_base_distribution.map((k) => k.name) ?? [],
  },
  series: [{
    type: 'bar',
    data: admin.dashboard?.knowledge_base_distribution.map((k) => k.document_count) ?? [],
  }],
}))
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-xl font-semibold">仪表盘</h1>
    <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <div v-for="s in stats" :key="s.label" class="rounded-lg border bg-background p-4">
        <div class="flex items-center justify-between">
          <p class="text-sm text-muted-foreground">{{ s.label }}</p>
          <component :is="s.icon" class="h-4 w-4 text-muted-foreground" />
        </div>
        <p class="mt-2 text-2xl font-semibold">{{ s.value }}</p>
      </div>
    </div>
    <div class="grid gap-4 lg:grid-cols-2">
      <div class="rounded-lg border bg-background p-4">
        <p class="mb-2 text-sm font-medium">问答趋势(近 7 天)</p>
        <Chart :option="trendOption" />
      </div>
      <div class="rounded-lg border bg-background p-4">
        <p class="mb-2 text-sm font-medium">文档处理状态</p>
        <Chart :option="statusOption" />
      </div>
      <div class="rounded-lg border bg-background p-4 lg:col-span-2">
        <p class="mb-2 text-sm font-medium">知识库文档分布</p>
        <Chart :option="distOption" />
      </div>
    </div>
  </div>
</template>
