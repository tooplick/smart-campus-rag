<script setup lang="ts">
// 模型配置:LLM / Embedding / Vision 三类 OpenAI 兼容模型的接入参数与连通性测试
import { onMounted, reactive, ref } from 'vue'
import { toast } from 'vue-sonner'
import { updateModel, testModel } from '@/api/admin'
import type { ModelTestResult } from '@/api/types'
import { errorMessage } from '@/utils/request'
import { formatDuration } from '@/utils/format'
import { useAdminStore } from '@/stores/admin'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'

const admin = useAdminStore()
const forms = reactive<Record<string, { base_url: string; api_key: string; model: string; enabled: boolean }>>({
  llm: { base_url: '', api_key: '', model: '', enabled: true },
  embedding: { base_url: '', api_key: '', model: '', enabled: true },
  vision: { base_url: '', api_key: '', model: '', enabled: true },
})
const testing = ref<Record<string, boolean>>({})
const testResults = ref<Record<string, ModelTestResult | null>>({})
const saving = ref<Record<string, boolean>>({})

const titles: Record<string, string> = { llm: 'LLM', embedding: 'Embedding', vision: 'Vision' }

onMounted(async () => {
  await admin.loadModels()
  for (const type of ['llm', 'embedding', 'vision']) {
    const c = admin.models?.[type as 'llm' | 'embedding' | 'vision']
    if (c) {
      forms[type].base_url = c.base_url
      forms[type].model = c.model
      forms[type].enabled = c.enabled
      // api_key 不回显,留空表示不修改
      forms[type].api_key = ''
    }
  }
})

async function save(type: string) {
  saving.value[type] = true
  try {
    const body: Record<string, unknown> = {
      base_url: forms[type].base_url, model: forms[type].model, enabled: forms[type].enabled,
    }
    if (forms[type].api_key) body.api_key = forms[type].api_key
    await updateModel(type, body)
    toast.success(`${titles[type]} 配置已保存`)
    forms[type].api_key = ''
    await admin.loadModels()
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    saving.value[type] = false
  }
}

async function onTest(type: string) {
  testing.value[type] = true
  testResults.value[type] = null
  try {
    // 后端始终返回 200,结果在 data.status
    testResults.value[type] = await testModel(type)
    const r = testResults.value[type]!
    if (r.status === 'ok') toast.success(`${titles[type]} 连接成功`)
    else toast.error(`${titles[type]} 连接失败`)
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    testing.value[type] = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-xl font-semibold">模型配置</h1>
    <div class="grid gap-4 lg:grid-cols-3">
      <div v-for="type in ['llm', 'embedding', 'vision']" :key="type" class="space-y-4 rounded-lg border bg-background p-4">
        <div class="flex items-center justify-between">
          <h2 class="font-medium">{{ titles[type] }}</h2>
          <Switch v-model="forms[type].enabled" />
        </div>
        <div class="space-y-2">
          <Label>Base URL</Label>
          <Input v-model="forms[type].base_url" placeholder="https://api.example.com/v1" />
        </div>
        <div class="space-y-2">
          <Label>API Key(留空不修改)</Label>
          <Input v-model="forms[type].api_key" type="password" :placeholder="admin.models?.[type as 'llm' | 'embedding' | 'vision']?.api_key_configured ? '已配置' : '未配置'" />
        </div>
        <div class="space-y-2">
          <Label>Model</Label>
          <Input v-model="forms[type].model" placeholder="model-name" />
        </div>
        <div class="flex gap-2">
          <Button :disabled="saving[type]" @click="save(type)">保存</Button>
          <Button variant="outline" :disabled="testing[type]" @click="onTest(type)">
            {{ testing[type] ? '测试中…' : '测试连接' }}
          </Button>
        </div>
        <div v-if="testResults[type]" class="rounded-md border p-2 text-xs">
          <template v-if="testResults[type]!.status === 'ok'">
            <p class="text-emerald-600">连接成功</p>
            <p class="text-muted-foreground">延迟 {{ formatDuration(testResults[type]!.latency_ms) }}</p>
            <p v-if="testResults[type]!.dimension" class="text-muted-foreground">向量维度 {{ testResults[type]!.dimension }}</p>
          </template>
          <p v-else class="text-destructive">连接失败</p>
        </div>
      </div>
    </div>
  </div>
</template>
