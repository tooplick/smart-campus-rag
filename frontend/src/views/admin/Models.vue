<script setup lang="ts">
// 模型配置:LLM / Embedding / Vision 三类 OpenAI 兼容模型的接入参数与连通性测试
// api_key 只写不回显,以「已配置/未配置」徽标提示;测试结果卡绿/红区分并展示延迟与维度
import { onMounted, reactive, ref } from 'vue'
import { toast } from 'vue-sonner'
import { AlertCircle, CircleCheck, CircleX, Loader2 } from '@lucide/vue'
import { updateModel, testModel } from '@/api/admin'
import type { ModelTestResult } from '@/api/types'
import { errorMessage } from '@/utils/request'
import { formatDuration } from '@/utils/format'
import { useAdminStore } from '@/stores/admin'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import EmptyState from '@/components/common/EmptyState.vue'

const admin = useAdminStore()
const forms = reactive<Record<string, { base_url: string; api_key: string; model: string; enabled: boolean }>>({
  llm: { base_url: '', api_key: '', model: '', enabled: true },
  embedding: { base_url: '', api_key: '', model: '', enabled: true },
  vision: { base_url: '', api_key: '', model: '', enabled: true },
  rerank: { base_url: '', api_key: '', model: '', enabled: true },
})
const testing = ref<Record<string, boolean>>({})
const testResults = ref<Record<string, ModelTestResult | null>>({})
const saving = ref<Record<string, boolean>>({})
const loading = ref(true)
const loadError = ref('')

const titles: Record<string, string> = { llm: 'LLM', embedding: 'Embedding', vision: 'Vision', rerank: 'Rerank(重排)' }

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    await admin.loadModels()
    for (const type of ['llm', 'embedding', 'vision', 'rerank']) {
      const c = admin.models?.[type as 'llm' | 'embedding' | 'vision' | 'rerank']
      if (c) {
        forms[type].base_url = c.base_url
        forms[type].model = c.model
        forms[type].enabled = c.enabled
        // api_key 不回显,留空表示不修改
        forms[type].api_key = ''
      }
    }
  } catch (e) {
    loadError.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function save(type: string) {
  if (saving.value[type]) return
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
  if (testing.value[type]) return
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

    <!-- 加载:三卡骨架 -->
    <div v-if="loading" class="grid gap-4 lg:grid-cols-3">
      <div v-for="i in 3" :key="i" class="space-y-4 rounded-lg border bg-background p-4">
        <Skeleton class="h-5 w-16" />
        <Skeleton class="h-8 w-full" />
        <Skeleton class="h-8 w-full" />
        <Skeleton class="h-8 w-full" />
        <Skeleton class="h-8 w-32" />
      </div>
    </div>

    <!-- 失败:页面内错误态 + 重试 -->
    <EmptyState
      v-else-if="loadError"
      :icon="AlertCircle" variant="error"
      title="模型配置加载失败" :description="loadError"
    >
      <template #action>
        <button class="rounded-md border px-4 py-2 text-sm hover:bg-accent" @click="load">重试</button>
      </template>
    </EmptyState>

    <div v-else class="grid gap-4 lg:grid-cols-3">
      <div v-for="type in ['llm', 'embedding', 'vision', 'rerank']" :key="type" class="space-y-4 rounded-lg border bg-background p-4">
        <div class="flex items-center justify-between">
          <h2 class="font-medium">{{ titles[type] }}</h2>
          <div class="flex items-center gap-2">
            <span class="text-xs text-muted-foreground">{{ forms[type].enabled ? '已启用' : '已停用' }}</span>
            <Switch v-model="forms[type].enabled" />
          </div>
        </div>
        <div class="space-y-1">
          <Label>Base URL</Label>
          <Input v-model="forms[type].base_url" placeholder="https://api.example.com/v1" />
        </div>
        <div class="space-y-1">
          <div class="flex items-center justify-between">
            <Label>API Key(留空不修改)</Label>
            <!-- api_key 不回显,以徽标提示是否已配置 -->
            <span
              class="rounded-full px-2 py-0.5 text-xs"
              :class="admin.models?.[type as 'llm' | 'embedding' | 'vision' | 'rerank']?.api_key_configured
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-muted text-muted-foreground'"
            >
              {{ admin.models?.[type as 'llm' | 'embedding' | 'vision' | 'rerank']?.api_key_configured ? '已配置' : '未配置' }}
            </span>
          </div>
          <Input v-model="forms[type].api_key" type="password"
            :placeholder="admin.models?.[type as 'llm' | 'embedding' | 'vision' | 'rerank']?.api_key_configured ? '输入新 Key 可替换' : '请输入 API Key'" />
        </div>
        <div class="space-y-1">
          <Label>Model</Label>
          <Input v-model="forms[type].model" placeholder="model-name" />
        </div>
        <div class="flex gap-2">
          <Button :disabled="saving[type]" @click="save(type)">
            <Loader2 v-if="saving[type]" class="mr-1 h-4 w-4 animate-spin" />
            {{ saving[type] ? '保存中…' : '保存' }}
          </Button>
          <Button variant="outline" :disabled="testing[type]" @click="onTest(type)">
            <Loader2 v-if="testing[type]" class="mr-1 h-4 w-4 animate-spin" />
            {{ testing[type] ? '测试中…' : '测试连接' }}
          </Button>
        </div>
        <!-- 测试结果卡:成功绿/失败红,图标 + 延迟/维度 -->
        <div v-if="testResults[type]" class="rounded-md border p-3 text-xs" :class="testResults[type]!.status === 'ok'
          ? 'border-emerald-200 bg-emerald-50'
          : 'border-red-200 bg-red-50'">
          <template v-if="testResults[type]!.status === 'ok'">
            <p class="flex items-center gap-1 font-medium text-emerald-700">
              <CircleCheck class="h-3.5 w-3.5" /> 连接成功
            </p>
            <p class="mt-1 text-muted-foreground">延迟 {{ formatDuration(testResults[type]!.latency_ms) }}</p>
            <p v-if="testResults[type]!.dimension" class="text-muted-foreground">向量维度 {{ testResults[type]!.dimension }}</p>
          </template>
          <template v-else>
            <p class="flex items-center gap-1 font-medium text-destructive">
              <CircleX class="h-3.5 w-3.5" /> 连接失败
            </p>
            <p class="mt-1 text-muted-foreground">请检查 Base URL、API Key 与 Model 配置后重试</p>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
