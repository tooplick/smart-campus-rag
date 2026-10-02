<script setup lang="ts">
// 单类型模型配置卡:展示启用配置、下拉切换、连通性测试、增删改(全部落盘配置文件)
// api_key 只写不回显;启用中的配置不可删(后端拒绝,前端也前置禁用)
import { computed, reactive, ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import { CircleCheck, CircleX, Loader2, Pencil, Plus, Trash2 } from '@lucide/vue'
import type { ModelProfileGroup, ModelTestResult, ModelType } from '@/api/types'
import { createModelProfile, deleteModelProfile, setActiveModelProfile, testModel, updateModelProfile } from '@/api/admin'
import { errorMessage } from '@/utils/request'
import { formatDuration } from '@/utils/format'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
    Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const props = defineProps<{
    type: ModelType
    title: string
    group: ModelProfileGroup
}>()
/** 配置清单变化后通知父级刷新 */
const emit = defineEmits<{ changed: [] }>()

/** Select 不能承载空值,用哨兵值表示「停用」(仅 vision/rerank 允许) */
const NONE = '__none__'
const optional = computed(() => props.type === 'vision' || props.type === 'rerank')

const profileNames = computed(() => Object.keys(props.group.profiles))
const activeProfile = computed(() =>
    props.group.active ? props.group.profiles[props.group.active] : null)

// ---------- 切换启用 ----------
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

// ---------- 测试 ----------
const testing = ref(false)
const testResult = ref<ModelTestResult | null>(null)
async function onTest() {
    if (testing.value) return
    if (!props.group.active) return toast.info('请先启用一套配置')
    testing.value = true
    testResult.value = null
    try {
        // 后端始终 200,结果在 data.status
        testResult.value = await testModel(props.type)
        if (testResult.value.status === 'ok') toast.success(`${props.title} 连接成功`)
        else toast.error(`${props.title} 连接失败`)
    } catch (e) {
        toast.error(errorMessage(e))
    } finally {
        testing.value = false
    }
}

// ---------- 添加 / 编辑 ----------
const dialogOpen = ref(false)
const editingName = ref<string | null>(null)
const saving = ref(false)
const touched = ref(false)
const form = reactive({ name: '', base_url: '', api_key: '', model: '' })

const nameError = computed(() => (form.name.trim() ? '' : '请输入配置名称'))
const urlError = computed(() => (form.base_url.trim() ? '' : '请输入 Base URL'))
const modelError = computed(() => (form.model.trim() ? '' : '请输入模型名'))

function openCreate() {
    editingName.value = null
    Object.assign(form, { name: '', base_url: '', api_key: '', model: '' })
    touched.value = false
    dialogOpen.value = true
}

function openEdit(name: string) {
    const p = props.group.profiles[name]
    editingName.value = name
    Object.assign(form, { name, base_url: p.base_url, api_key: '', model: p.model })
    touched.value = false
    dialogOpen.value = true
}

async function save() {
    touched.value = true
    if (nameError.value || urlError.value || modelError.value) return
    saving.value = true
    try {
        if (editingName.value) {
            // 编辑:api_key 留空表示不修改;名称不可改(路径即标识)
            await updateModelProfile(props.type, editingName.value, {
                base_url: form.base_url.trim(),
                model: form.model.trim(),
                ...(form.api_key ? { api_key: form.api_key } : {}),
            })
            toast.success('配置已保存')
        } else {
            await createModelProfile({
                type: props.type,
                name: form.name.trim(),
                base_url: form.base_url.trim(),
                api_key: form.api_key.trim(),
                model: form.model.trim(),
            })
            toast.success('配置已添加')
        }
        dialogOpen.value = false
        emit('changed')
    } catch (e) {
        toast.error(errorMessage(e))
    } finally {
        saving.value = false
    }
}

// ---------- 删除 ----------
const deleteName = ref<string | null>(null)
const confirmOpen = ref(false)
function askDelete(name: string) {
    deleteName.value = name
    confirmOpen.value = true
}
async function onConfirmDelete() {
    if (!deleteName.value) return
    try {
        await deleteModelProfile(props.type, deleteName.value)
        toast.success('配置已删除')
        emit('changed')
    } catch (e) {
        toast.error(errorMessage(e))
    }
}

// 组变化时关掉残留弹窗(父级刷新可能发生在操作后)
watch(() => props.group, () => { confirmOpen.value = false })
</script>

<template>
    <div class="space-y-4 rounded-lg border bg-background p-4">
        <div class="flex items-center justify-between">
            <h2 class="font-medium">{{ title }}</h2>
            <span class="rounded-full px-2 py-0.5 text-xs"
                :class="group.active ? 'bg-emerald-100 text-emerald-700' : 'bg-muted text-muted-foreground'">
                {{ group.active ? `已启用:${group.active}` : '未启用' }}
            </span>
        </div>

        <!-- 当前启用配置 -->
        <div v-if="activeProfile" class="space-y-1 rounded-md bg-muted/50 p-3 text-xs text-muted-foreground">
            <p class="truncate">Base URL:{{ activeProfile.base_url }}</p>
            <p class="truncate">Model:{{ activeProfile.model }}</p>
            <p>API Key:{{ activeProfile.api_key_configured ? '已配置' : '未配置' }}</p>
        </div>
        <p v-else class="rounded-md bg-muted/50 p-3 text-xs text-muted-foreground">
            尚无配置,点击「添加配置」创建{{ optional ? ';本类型支持停用' : ',首个配置将自动启用' }}
        </p>

        <!-- 切换启用 + 测试 -->
        <div class="flex gap-2">
            <Select :model-value="group.active ?? NONE" :disabled="!profileNames.length || switching"
                @update:model-value="onSwitch">
                <SelectTrigger class="min-w-0 flex-1">
                    <SelectValue placeholder="切换启用配置" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem v-for="name in profileNames" :key="name" :value="name">{{ name }}</SelectItem>
                    <SelectItem v-if="optional && group.active" :value="NONE">停用</SelectItem>
                </SelectContent>
            </Select>
            <Button variant="outline" :disabled="testing || !group.active" @click="onTest">
                <Loader2 v-if="testing" class="mr-1 h-4 w-4 animate-spin" />
                {{ testing ? '测试中…' : '测试' }}
            </Button>
        </div>

        <!-- 测试结果 -->
        <div v-if="testResult" class="rounded-md border p-3 text-xs" :class="testResult.status === 'ok'
            ? 'border-emerald-200 bg-emerald-50' : 'border-red-200 bg-red-50'">
            <template v-if="testResult.status === 'ok'">
                <p class="flex items-center gap-1 font-medium text-emerald-700">
                    <CircleCheck class="h-3.5 w-3.5" /> 连接成功
                </p>
                <p class="mt-1 text-muted-foreground">延迟 {{ formatDuration(testResult.latency_ms) }}</p>
                <p v-if="testResult.dimension" class="text-muted-foreground">向量维度 {{ testResult.dimension }}</p>
            </template>
            <template v-else>
                <p class="flex items-center gap-1 font-medium text-destructive">
                    <CircleX class="h-3.5 w-3.5" /> 连接失败
                </p>
                <p class="mt-1 text-muted-foreground">请检查 Base URL、API Key 与 Model 配置后重试</p>
            </template>
        </div>

        <!-- 配置清单 -->
        <div class="space-y-1.5">
            <p class="text-xs font-medium text-muted-foreground">配置清单</p>
            <div v-for="name in profileNames" :key="name"
                class="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
                <span class="min-w-0 flex-1 truncate" :class="{ 'font-medium': name === group.active }">
                    {{ name }}
                    <span class="ml-1 text-xs text-muted-foreground">{{ group.profiles[name].model }}</span>
                </span>
                <button class="rounded p-1 text-muted-foreground hover:bg-accent" title="编辑" @click="openEdit(name)">
                    <Pencil class="h-3.5 w-3.5" />
                </button>
                <button class="rounded p-1 text-muted-foreground hover:bg-accent disabled:opacity-40" title="删除"
                    :disabled="name === group.active" @click="askDelete(name)">
                    <Trash2 class="h-3.5 w-3.5" />
                </button>
            </div>
            <p v-if="!profileNames.length" class="px-1 text-xs text-muted-foreground">暂无配置</p>
        </div>

        <Button variant="outline" size="sm" class="w-full" @click="openCreate">
            <Plus class="mr-1 h-4 w-4" /> 添加配置
        </Button>

        <!-- 添加/编辑对话框 -->
        <Dialog v-model:open="dialogOpen">
            <DialogContent class="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>{{ editingName ? `编辑配置:${editingName}` : `添加${title}配置` }}</DialogTitle>
                </DialogHeader>
                <div class="space-y-4">
                    <div class="space-y-1">
                        <Label for="pf-name">配置名称</Label>
                        <Input id="pf-name" v-model="form.name" :disabled="Boolean(editingName)"
                            placeholder="如 default、mimo" @blur="touched = true" />
                        <p v-if="touched && nameError" class="text-xs text-destructive">{{ nameError }}</p>
                        <p v-else-if="editingName" class="text-xs text-muted-foreground">名称即标识,不可修改</p>
                    </div>
                    <div class="space-y-1">
                        <Label for="pf-url">Base URL</Label>
                        <Input id="pf-url" v-model="form.base_url" placeholder="https://api.example.com/v1"
                            @blur="touched = true" />
                        <p v-if="touched && urlError" class="text-xs text-destructive">{{ urlError }}</p>
                    </div>
                    <div class="space-y-1">
                        <Label for="pf-key">API Key</Label>
                        <Input id="pf-key" v-model="form.api_key" type="password"
                            :placeholder="editingName ? '留空表示不修改' : '可选,本地服务可留空'" />
                    </div>
                    <div class="space-y-1">
                        <Label for="pf-model">Model</Label>
                        <Input id="pf-model" v-model="form.model" placeholder="model-name" @blur="touched = true" />
                        <p v-if="touched && modelError" class="text-xs text-destructive">{{ modelError }}</p>
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" @click="dialogOpen = false">取消</Button>
                    <Button :disabled="saving" @click="save">
                        <Loader2 v-if="saving" class="mr-1 h-4 w-4 animate-spin" />
                        {{ saving ? '保存中…' : '保存' }}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>

        <ConfirmDialog v-model:open="confirmOpen" title="删除配置" description="删除后不可恢复;启用中的配置需先切换到其他配置才能删除。"
            @confirm="onConfirmDelete" />
    </div>
</template>
