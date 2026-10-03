<script setup lang="ts">
// RAG 管线参数表单(自原 /RagConfig 页迁入,供设置页复用):
// 全部参数可编辑,保存即热更新到运行中的管线(无需重启)
// 校验即时内联到字段(输入即生效),保存时兜底拦截;加载失败组件内重试
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import { AlertCircle, Loader2 } from '@lucide/vue'
import { saveRagConfig } from '@/api/admin'
import { errorMessage } from '@/utils/request'
import { useAdminStore } from '@/stores/admin'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import EmptyState from '@/components/common/EmptyState.vue'

const admin = useAdminStore()
const form = reactive({
    chunk_size: 600, chunk_overlap: 80,
    candidate_top_k: 8, final_top_k: 5, similarity_threshold: 0.6,
    vector_weight: 0.7, auto_keywords: 5, auto_questions: 2,
    temperature: 0.2, max_tokens: 2048,
    embedding_batch_size: 32, embedding_max_retries: 3,
    llm_max_retries: 3, request_timeout: 120,
})
const loading = ref(true)
// 失败仅驱动「通用错误态 + 重试」,具体原因走顶部居中 toast
const failed = ref(false)
const saving = ref(false)

/** 各参数的说明文案(含义与取值范围) */
const fields = [
    { key: 'chunk_size', label: 'Chunk Size', hint: '文本切块的最大长度(字符数),范围 100~4000', step: undefined },
    { key: 'chunk_overlap', label: 'Chunk Overlap', hint: '相邻切块的重叠字符数,需 ≥0 且小于 Chunk Size', step: undefined },
    { key: 'candidate_top_k', label: 'Candidate Top-K', hint: '向量检索召回的候选切片数,范围 1~50', step: undefined },
    { key: 'final_top_k', label: 'Final Top-K', hint: '送入模型上下文的最终切片数,需 ≥1 且不大于 Candidate Top-K', step: undefined },
    { key: 'similarity_threshold', label: 'Similarity Threshold', hint: '相似度阈值(对混合检索融合分),低于该值的切片被过滤,范围 0~1', step: 0.05 },
    { key: 'vector_weight', label: 'Vector Weight(向量权重)', hint: '混合检索中向量路的权重 0~1;调低偏关键词精确匹配(人名/编号),调高偏语义', step: 0.05 },
    { key: 'auto_keywords', label: 'Auto Keywords(入库增强)', hint: '每切片生成的关键词数,0=关闭,范围 0~20', step: 1 },
    { key: 'auto_questions', label: 'Auto Questions(入库增强)', hint: '每切片生成的候选问题数,0=关闭,范围 0~10', step: 1 },
    { key: 'temperature', label: 'Temperature(生成随机性)', hint: '回答的发散程度 0~2;低值更严谨稳定,高值更多样发散', step: 0.1 },
    { key: 'max_tokens', label: 'Max Tokens(生成长度)', hint: '单次回答的最大生成长度,范围 64~8192', step: 64 },
] as const

/** 可选运行参数:调用次数/批量相关,默认值即开箱即用,一般无需改动 */
const runtimeFields = [
    { key: 'embedding_batch_size', label: 'Embedding Batch Size', hint: '单批向量化条数,范围 1~1024;调大可加快入库,过大会撑爆模型上下文', step: 1 },
    { key: 'embedding_max_retries', label: 'Embedding 重试次数', hint: 'Embedding 请求失败后的重试次数,范围 0~10', step: 1 },
    { key: 'llm_max_retries', label: 'LLM 重试次数', hint: 'LLM 请求失败后的重试次数,范围 0~10', step: 1 },
    { key: 'request_timeout', label: '请求超时(秒)', hint: 'LLM/Embedding 单次请求超时,范围 1~600;慢模型或大批量入库可调大', step: 10 },
] as const

// store 中的配置到达后回填表单
watch(() => admin.ragConfig, (c) => {
    if (!c) return
    form.chunk_size = c.chunk_size
    form.chunk_overlap = c.chunk_overlap
    form.candidate_top_k = c.candidate_top_k
    form.final_top_k = c.final_top_k
    form.similarity_threshold = c.similarity_threshold
    form.vector_weight = c.vector_weight
    form.auto_keywords = c.auto_keywords
    form.auto_questions = c.auto_questions
    form.temperature = c.temperature
    form.max_tokens = c.max_tokens
    form.embedding_batch_size = c.embedding_batch_size
    form.embedding_max_retries = c.embedding_max_retries
    form.llm_max_retries = c.llm_max_retries
    form.request_timeout = c.request_timeout
}, { immediate: true })

async function load() {
    loading.value = true
    failed.value = false
    try {
        await admin.loadRagConfig()
    } catch (e) {
        failed.value = true
        toast.error(errorMessage(e))
    } finally {
        loading.value = false
    }
}

onMounted(load)

/** 逐字段即时校验(与后端约束一致),输入变化即反映到字段下方 */
const errors = computed(() => {
    const e: Record<string, string> = {}
    if (form.chunk_size < 100 || form.chunk_size > 4000) e.chunk_size = 'Chunk Size 需在 100~4000 之间'
    if (form.chunk_overlap < 0 || form.chunk_overlap >= form.chunk_size) e.chunk_overlap = 'Chunk Overlap 需 ≥0 且小于 Chunk Size'
    if (form.candidate_top_k < 1 || form.candidate_top_k > 50) e.candidate_top_k = 'Candidate Top-K 需在 1~50 之间'
    if (form.final_top_k < 1 || form.final_top_k > form.candidate_top_k) e.final_top_k = 'Final Top-K 需 ≥1 且不大于 Candidate Top-K'
    if (form.similarity_threshold < 0 || form.similarity_threshold > 1) e.similarity_threshold = 'Similarity Threshold 需在 0~1 之间'
    if (form.vector_weight < 0 || form.vector_weight > 1) e.vector_weight = 'Vector Weight 需在 0~1 之间'
    if (form.auto_keywords < 0 || form.auto_keywords > 20) e.auto_keywords = 'Auto Keywords 需在 0~20 之间'
    if (form.auto_questions < 0 || form.auto_questions > 10) e.auto_questions = 'Auto Questions 需在 0~10 之间'
    if (form.temperature < 0 || form.temperature > 2) e.temperature = 'Temperature 需在 0~2 之间'
    if (form.max_tokens < 64 || form.max_tokens > 8192) e.max_tokens = 'Max Tokens 需在 64~8192 之间'
    if (form.embedding_batch_size < 1 || form.embedding_batch_size > 1024) e.embedding_batch_size = 'Embedding Batch Size 需在 1~1024 之间'
    if (form.embedding_max_retries < 0 || form.embedding_max_retries > 10) e.embedding_max_retries = 'Embedding 重试次数需在 0~10 之间'
    if (form.llm_max_retries < 0 || form.llm_max_retries > 10) e.llm_max_retries = 'LLM 重试次数需在 0~10 之间'
    if (form.request_timeout < 1 || form.request_timeout > 600) e.request_timeout = '请求超时需在 1~600 秒之间'
    return e
})
const hasError = computed(() => Object.keys(errors.value).length > 0)

async function save() {
    if (hasError.value) return toast.error('请先修正表单中的错误')
    saving.value = true
    try {
        await saveRagConfig({ ...form })
        toast.success('配置已保存,即时生效')
        await admin.loadRagConfig()
    } catch (e) {
        toast.error(errorMessage(e))
    } finally {
        saving.value = false
    }
}
</script>

<template>
    <div class="space-y-4">
        <!-- 加载:表单骨架 -->
        <div v-if="loading" class="space-y-4 rounded-lg border bg-background p-6">
            <div class="grid grid-cols-2 gap-4">
                <div v-for="i in 5" :key="i" class="space-y-2">
                    <Skeleton class="h-4 w-24" />
                    <Skeleton class="h-8 w-full" />
                </div>
            </div>
        </div>

        <!-- 失败:组件内错误态 + 重试 -->
        <EmptyState v-else-if="failed" :icon="AlertCircle" variant="error" title="RAG 配置加载失败">
            <template #action>
                <button class="rounded-md border px-4 py-2 text-sm hover:bg-accent" @click="load">重试</button>
            </template>
        </EmptyState>

        <div v-else class="space-y-6 rounded-lg border bg-background p-6">
            <div class="grid gap-4 sm:grid-cols-2">
                <div v-for="f in fields" :key="f.key" class="space-y-1">
                    <Label :for="f.key">{{ f.label }}</Label>
                    <Input :id="f.key" v-model.number="form[f.key]" type="number" :step="f.step"
                        :aria-invalid="Boolean(errors[f.key])" />
                    <!-- 说明文案与内联错误分层:错误出现时替换说明位,高度稳定不跳版 -->
                    <p v-if="errors[f.key]" class="min-h-4 text-xs text-destructive">{{ errors[f.key] }}</p>
                    <p v-else class="min-h-4 text-xs text-muted-foreground">{{ f.hint }}</p>
                </div>
            </div>

            <!-- 可选运行参数:与常规参数分组,避免淹没主表单 -->
            <div class="space-y-3 border-t pt-4">
                <div>
                    <h3 class="text-sm font-medium">运行参数(可选)</h3>
                    <p class="text-xs text-muted-foreground">批量、重试与超时;默认值开箱即用,无需改动</p>
                </div>
                <div class="grid gap-4 sm:grid-cols-2">
                    <div v-for="f in runtimeFields" :key="f.key" class="space-y-1">
                        <Label :for="f.key">{{ f.label }}</Label>
                        <Input :id="f.key" v-model.number="form[f.key]" type="number" :step="f.step"
                            :aria-invalid="Boolean(errors[f.key])" />
                        <p v-if="errors[f.key]" class="min-h-4 text-xs text-destructive">{{ errors[f.key] }}</p>
                        <p v-else class="min-h-4 text-xs text-muted-foreground">{{ f.hint }}</p>
                    </div>
                </div>
            </div>

            <Button :disabled="saving || hasError" @click="save">
                <Loader2 v-if="saving" class="mr-1 h-4 w-4 animate-spin" />
                {{ saving ? '保存中…' : '保存配置' }}
            </Button>
        </div>
    </div>
</template>
