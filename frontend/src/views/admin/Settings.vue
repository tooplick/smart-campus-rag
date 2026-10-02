<script setup lang="ts">
// 设置页(/Settings):替换原「RAG 配置」与「模型」两页
// 上区:四类模型配置(读写 app-config.yaml,切换热替换);下区:RAG 参数(保存即热更新)
import { onMounted, ref } from 'vue'
import { toast } from 'vue-sonner'
import { AlertCircle, Cpu } from '@lucide/vue'
import { errorMessage } from '@/utils/request'
import { useAdminStore } from '@/stores/admin'
import ModelProfilesCard from '@/components/admin/ModelProfilesCard.vue'
import RagParamsForm from '@/components/admin/RagParamsForm.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { Skeleton } from '@/components/ui/skeleton'

const admin = useAdminStore()
const loading = ref(true)
const loadError = ref('')

const cards = [
    { type: 'llm', title: '对话 LLM' },
    { type: 'embedding', title: 'Embedding' },
    { type: 'vision', title: 'Vision' },
    { type: 'rerank', title: 'Rerank(重排)' },
] as const

async function load() {
    loading.value = true
    loadError.value = ''
    try {
        await admin.loadModelProfiles()
    } catch (e) {
        loadError.value = errorMessage(e)
    } finally {
        loading.value = false
    }
}

onMounted(load)

/** 配置清单变化后重拉(卡片操作完成时触发) */
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
                模型配置与 RAG 参数统一写入 <code class="rounded bg-muted px-1">app-config.yaml</code>,保存即生效
            </p>
        </div>

        <!-- 模型配置区 -->
        <section class="space-y-4">
            <h2 class="text-sm font-medium text-muted-foreground">模型配置</h2>

            <div v-if="loading" class="grid gap-4 lg:grid-cols-2">
                <div v-for="i in 4" :key="i" class="space-y-4 rounded-lg border bg-background p-4">
                    <Skeleton class="h-5 w-24" />
                    <Skeleton class="h-16 w-full" />
                    <Skeleton class="h-9 w-full" />
                    <Skeleton class="h-9 w-32" />
                </div>
            </div>

            <EmptyState v-else-if="loadError" :icon="AlertCircle" variant="error" title="模型配置加载失败"
                :description="loadError">
                <template #action>
                    <button class="rounded-md border px-4 py-2 text-sm hover:bg-accent" @click="load">重试</button>
                </template>
            </EmptyState>

            <div v-else class="grid gap-4 lg:grid-cols-2">
                <ModelProfilesCard v-for="c in cards" :key="c.type" :type="c.type" :title="c.title"
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
