<script setup lang="ts">
// 设置页(/Settings):决定「用哪套模型配置」+ RAG 参数(均保存即生效)
// 配置的增删改在「模型」页(/Model),本页只做选择与参数调整
import { onMounted, ref } from 'vue'
import { toast } from 'vue-sonner'
import { AlertCircle, Boxes, Cpu } from '@lucide/vue'
import { errorMessage } from '@/utils/request'
import { useAdminStore } from '@/stores/admin'
import ModelSelector from '@/components/admin/ModelSelector.vue'
import RagParamsForm from '@/components/admin/RagParamsForm.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { Skeleton } from '@/components/ui/skeleton'

const admin = useAdminStore()
const loading = ref(true)
// 失败仅驱动「通用错误态 + 重试」,具体原因走顶部居中 toast
const failed = ref(false)

const cards = [
    { type: 'llm', title: '对话 LLM' },
    { type: 'embedding', title: 'Embedding' },
    { type: 'vision', title: 'Vision' },
    { type: 'rerank', title: 'Rerank(重排)' },
] as const

async function load() {
    loading.value = true
    failed.value = false
    try {
        await admin.loadModelProfiles()
    } catch (e) {
        failed.value = true
        toast.error(errorMessage(e))
    } finally {
        loading.value = false
    }
}

onMounted(load)

/** 启用配置切换后重拉(下拉操作完成时触发) */
async function onChanged() {
    try {
        await admin.loadModelProfiles()
    } catch (e) {
        toast.error(errorMessage(e))
    }
}
</script>

<template>
    <div class="mx-auto max-w-5xl space-y-8">
        <div>
            <h1 class="text-xl font-semibold">设置</h1>
            <p class="mt-1 text-sm text-muted-foreground">
                在这里选择各类模型当前使用的配置(切换即热替换,立即生效);配置的增删改在「模型」页
            </p>
        </div>

        <!-- 使用模型:四类各一个下拉 -->
        <section class="space-y-4">
            <div class="flex items-center gap-2">
                <Boxes class="h-4 w-4 text-muted-foreground" />
                <h2 class="text-sm font-medium text-muted-foreground">使用模型</h2>
            </div>

            <div v-if="loading" class="grid gap-3">
                <Skeleton v-for="i in 4" :key="i" class="h-14 rounded-lg" />
            </div>

            <EmptyState v-else-if="failed" :icon="AlertCircle" variant="error" title="模型配置加载失败">
                <template #action>
                    <button class="rounded-md border px-4 py-2 text-sm hover:bg-accent" @click="load">重试</button>
                </template>
            </EmptyState>

            <div v-else class="grid gap-3">
                <ModelSelector v-for="c in cards" :key="c.type" :type="c.type" :title="c.title"
                    :group="admin.modelProfiles![c.type]" @changed="onChanged" />
            </div>
        </section>

        <!-- RAG 参数区 -->
        <section class="space-y-4">
            <div class="flex items-center gap-2">
                <Cpu class="h-4 w-4 text-muted-foreground" />
                <h2 class="text-sm font-medium text-muted-foreground">RAG 参数</h2>
            </div>
            <RagParamsForm />
        </section>
    </div>
</template>
