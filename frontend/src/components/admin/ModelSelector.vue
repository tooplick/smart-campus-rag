<script setup lang="ts">
// 设置页「使用模型」选择器:每类模型一个下拉,决定当前启用哪套配置(切换即热替换生效)
// 配置的增删改在「模型」页(/Model),本组件只管「用哪套」
import { computed, ref } from 'vue'
import { toast } from 'vue-sonner'
import type { ModelProfileGroup, ModelType } from '@/api/types'
import { setActiveModelProfile } from '@/api/admin'
import { errorMessage } from '@/utils/request'
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'

const props = defineProps<{
    type: ModelType
    title: string
    group: ModelProfileGroup
}>()
const emit = defineEmits<{ changed: [] }>()

/** Select 不能承载空值,用哨兵值表示「停用」(仅 vision/rerank 允许) */
const NONE = '__none__'
const optional = computed(() => props.type === 'vision' || props.type === 'rerank')

const profileNames = computed(() => Object.keys(props.group.profiles))
const activeProfile = computed(() =>
    props.group.active ? props.group.profiles[props.group.active] : null)

const switching = ref(false)
async function onSwitch(value: unknown) {
    if (switching.value) return
    switching.value = true
    try {
        await setActiveModelProfile(props.type, value === NONE ? null : String(value))
        toast.success(value === NONE ? `${props.title} 已停用` : `已切换到 ${String(value)}`)
        emit('changed')
    } catch (e) {
        toast.error(errorMessage(e))
    } finally {
        switching.value = false
    }
}
</script>

<template>
    <div class="flex items-center gap-3 rounded-lg border bg-background p-3">
        <!-- 左侧:类型 + 当前使用的模型名 -->
        <div class="w-36 shrink-0 min-w-0">
            <p class="text-sm font-medium">{{ title }}</p>
            <p class="truncate text-xs text-muted-foreground" :title="activeProfile?.model">
                {{ activeProfile ? activeProfile.model : '未启用' }}
            </p>
        </div>
        <!-- 右侧:启用哪套配置 -->
        <Select :model-value="group.active ?? NONE" :disabled="!profileNames.length || switching"
            @update:model-value="onSwitch">
            <SelectTrigger class="min-w-0 flex-1">
                <SelectValue placeholder="选择使用的配置(暂无配置请到「模型」页添加)" />
            </SelectTrigger>
            <SelectContent>
                <SelectItem v-for="name in profileNames" :key="name" :value="name">{{ name }}</SelectItem>
                <SelectItem v-if="optional && group.active" :value="NONE">停用</SelectItem>
            </SelectContent>
        </Select>
    </div>
</template>
