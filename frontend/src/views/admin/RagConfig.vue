<script setup lang="ts">
// RAG 管线参数配置:可编辑 5 项核心参数,temperature / max_tokens 只读展示
import { onMounted, reactive, ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import { saveRagConfig } from '@/api/admin'
import { errorMessage } from '@/utils/request'
import { useAdminStore } from '@/stores/admin'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const admin = useAdminStore()
const form = reactive({
  chunk_size: 600, chunk_overlap: 80,
  candidate_top_k: 8, final_top_k: 5, similarity_threshold: 0.6,
})
const loading = ref(false)

// store 中的配置到达后回填表单
watch(() => admin.ragConfig, (c) => {
  if (!c) return
  form.chunk_size = c.chunk_size
  form.chunk_overlap = c.chunk_overlap
  form.candidate_top_k = c.candidate_top_k
  form.final_top_k = c.final_top_k
  form.similarity_threshold = c.similarity_threshold
}, { immediate: true })

onMounted(() => admin.loadRagConfig())

/** 前端预校验,与后端约束一致 */
function validate(): string | null {
  if (form.chunk_size < 100 || form.chunk_size > 4000) return 'Chunk Size 需在 100~4000 之间'
  if (form.chunk_overlap < 0 || form.chunk_overlap >= form.chunk_size) return 'Chunk Overlap 需 ≥0 且小于 Chunk Size'
  if (form.candidate_top_k < 1 || form.candidate_top_k > 50) return 'Candidate Top-K 需在 1~50 之间'
  if (form.final_top_k < 1 || form.final_top_k > form.candidate_top_k) return 'Final Top-K 需 ≥1 且不大于 Candidate Top-K'
  if (form.similarity_threshold < 0 || form.similarity_threshold > 1) return 'Similarity Threshold 需在 0~1 之间'
  return null
}

async function save() {
  const err = validate()
  if (err) return toast.error(err)
  loading.value = true
  try {
    await saveRagConfig({ ...form })
    toast.success('配置已保存')
    await admin.loadRagConfig()
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl space-y-6">
    <h1 class="text-xl font-semibold">RAG 配置</h1>
    <div class="space-y-4 rounded-lg border bg-background p-6">
      <div class="grid grid-cols-2 gap-4">
        <div class="space-y-2">
          <Label for="chunk_size">Chunk Size</Label>
          <Input id="chunk_size" v-model.number="form.chunk_size" type="number" />
        </div>
        <div class="space-y-2">
          <Label for="chunk_overlap">Chunk Overlap</Label>
          <Input id="chunk_overlap" v-model.number="form.chunk_overlap" type="number" />
        </div>
        <div class="space-y-2">
          <Label for="candidate_top_k">Candidate Top-K</Label>
          <Input id="candidate_top_k" v-model.number="form.candidate_top_k" type="number" />
        </div>
        <div class="space-y-2">
          <Label for="final_top_k">Final Top-K</Label>
          <Input id="final_top_k" v-model.number="form.final_top_k" type="number" />
        </div>
        <div class="space-y-2">
          <Label for="threshold">Similarity Threshold</Label>
          <Input id="threshold" v-model.number="form.similarity_threshold" type="number" step="0.05" />
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4 border-t pt-4">
        <div class="space-y-2">
          <Label>Temperature(只读)</Label>
          <Input :model-value="admin.ragConfig?.temperature ?? '—'" disabled />
        </div>
        <div class="space-y-2">
          <Label>Max Tokens(只读)</Label>
          <Input :model-value="admin.ragConfig?.max_tokens ?? '—'" disabled />
        </div>
      </div>
      <Button :disabled="loading" @click="save">{{ loading ? '保存中…' : '保存配置' }}</Button>
    </div>
  </div>
</template>
