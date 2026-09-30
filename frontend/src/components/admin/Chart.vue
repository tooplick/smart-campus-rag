<script setup lang="ts">
// ECharts 封装:负责初始化、随 option 更新重绘、窗口缩放自适应与卸载销毁
import { onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{ option: echarts.EChartsOption }>()
const el = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function render() {
  if (!el.value) return
  if (!chart) chart = echarts.init(el.value)
  chart.setOption(props.option)
}

const onResize = () => chart?.resize()

onMounted(() => {
  render()
  window.addEventListener('resize', onResize)
})

watch(() => props.option, render, { deep: true })

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
})
</script>

<template>
  <div ref="el" class="h-64 w-full" />
</template>
