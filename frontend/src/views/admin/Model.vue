<script setup lang="ts">
// 模型页(/Model/{type}):四类模型子菜单 + 当前类型配置列表(表格)
// 含增删改 / 拉取模型名 / 连通性测试;「用哪套配置」的启用切换在设置页
// api_key 只写不回显;启用中的配置不可删
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
import { Activity, AlertCircle, CircleCheck, CircleX, Loader2, Pencil, Plus, Trash2 } from '@lucide/vue'
import type { ModelProfileGroup, ModelTestResult, ModelType } from '@/api/types'
import { createModelProfile, deleteModelProfile, fetchRemoteModels, testModel, updateModelProfile } from '@/api/admin'
import { errorMessage } from '@/utils/request'
import { formatDuration } from '@/utils/format'
import { useAdminStore } from '@/stores/admin'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
    Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import EmptyState from '@/components/common/EmptyState.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const props = defineProps<{ type: ModelType; title: string }>()
const route = useRoute()
const admin = useAdminStore()

// ---------- 子菜单 ----------
const tabs = [
    { to: '/Model/llm', label: '对话 LLM' },
    { to: '/Model/embedding', label: 'Embedding' },
    { to: '/Model/vision', label: 'Vision' },
    { to: '/Model/rerank', label: 'Rerank(重排)' },
]

/** 子菜单高亮:前缀匹配 */
function isActive(to: string) {
    return route.path.toLowerCase().startsWith(to.toLowerCase())
}

// ---------- 加载 ----------
const loading = ref(true)
// 失败仅驱动「通用错误态 + 重试」,具体原因走顶部居中 toast
const failed = ref(false)

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

// ---------- 当前类型数据 ----------
const group = computed<ModelProfileGroup>(() =>
    admin.modelProfiles?.[props.type] ?? { active: null, profiles: {} })
const profileNames = computed(() => Object.keys(group.value.profiles))

/** 操作后重拉配置清单(失败顶部居中 toast) */
async function reload() {
    try {
        await admin.loadModelProfiles()
    } catch (e) {
        toast.error(errorMessage(e))
    }
}

// 切换子菜单复用本组件:清理上一类残留的弹窗/测试结果
watch(() => props.type, () => {
    dialogOpen.value = false
    confirmOpen.value = false
    testResults.value = {}
    touched.value = false
})

// ---------- 测试:结果按配置名挂在对应配置条(表格行)下方 ----------
const testingName = ref<string | null>(null)
const testResults = ref<Record<string, ModelTestResult>>({})

async function runTest(name?: string) {
    if (testingName.value) return
    const target = name ?? group.value.active
    if (!target) return toast.info('暂无启用配置,请到「设置」页选择使用的模型')
    testingName.value = target
    try {
        // 后端始终 200,结果在 data.status;name 缺省测启用配置
        const r = await testModel(props.type, name ? target : undefined)
        testResults.value = { ...testResults.value, [target]: r }
        if (r.status === 'ok') toast.success(`${target} 连接成功`)
        else toast.error(`${target} 连接失败,请检查 Base URL、API Key 与 Model 配置后重试`)
    } catch (e) {
        toast.error(errorMessage(e))
    } finally {
        testingName.value = null
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

// ---------- 拉取远端模型列表(新建/编辑时下拉候选,点击回填) ----------
const fetchingModels = ref(false)
const modelOptions = ref<string[]>([])

async function fetchModels() {
    if (fetchingModels.value) return
    if (!form.base_url.trim()) {
        touched.value = true
        return toast.error('请先填写 Base URL')
    }
    fetchingModels.value = true
    try {
        const { models } = await fetchRemoteModels(form.base_url.trim(), form.api_key.trim())
        modelOptions.value = models
        if (models.length) toast.success(`获取到 ${models.length} 个可用模型`)
        else toast.info('该服务未返回模型列表,请手动输入模型名')
    } catch (e) {
        modelOptions.value = []
        toast.error(errorMessage(e))
    } finally {
        fetchingModels.value = false
    }
}

function openCreate() {
    editingName.value = null
    Object.assign(form, { name: '', base_url: '', api_key: '', model: '' })
    touched.value = false
    modelOptions.value = []
    dialogOpen.value = true
}

function openEdit(name: string) {
    const p = group.value.profiles[name]
    editingName.value = name
    Object.assign(form, { name, base_url: p.base_url, api_key: '', model: p.model })
    touched.value = false
    modelOptions.value = []
    dialogOpen.value = true
}

async function save() {
    touched.value = true
    // 校验不通过:首条错误顶部居中 toast 弹出(字段行内红字同步标出)
    if (nameError.value || urlError.value || modelError.value) {
        toast.error(nameError.value || urlError.value || modelError.value)
        return
    }
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
        await reload()
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
        await reload()
    } catch (e) {
        toast.error(errorMessage(e))
    }
}
</script>

<template>
    <div class="mx-auto max-w-5xl space-y-6">
        <div>
            <h1 class="text-xl font-semibold">模型配置</h1>
            <p class="mt-1 text-sm text-muted-foreground">
                在这里维护四类模型的配置(列表展示、增删改、连通性测试),统一写入
                <code class="rounded bg-muted px-1">app-config.yaml</code>;
                「用哪套配置」在「设置」页切换
            </p>
        </div>

        <!-- 子菜单:四类模型 -->
        <nav class="flex gap-1 overflow-x-auto border-b">
            <router-link v-for="tab in tabs" :key="tab.to" :to="tab.to"
                class="shrink-0 border-b-2 px-3 py-2 text-sm transition-colors" :class="isActive(tab.to)
                    ? 'border-foreground font-medium text-foreground'
                    : 'border-transparent text-muted-foreground hover:text-foreground'">
                {{ tab.label }}
            </router-link>
        </nav>

        <!-- 加载:列表骨架 -->
        <div v-if="loading" class="space-y-3">
            <Skeleton class="h-10 w-full" />
            <Skeleton class="h-44 w-full" />
        </div>

        <EmptyState v-else-if="failed" :icon="AlertCircle" variant="error" title="模型配置加载失败">
            <template #action>
                <button class="rounded-md border px-4 py-2 text-sm hover:bg-accent" @click="load">重试</button>
            </template>
        </EmptyState>

        <!-- 当前类型的配置列表 -->
        <div v-else class="space-y-4">
            <!-- 工具条:清单概览 + 测试 + 添加 -->
            <div class="flex items-center justify-between gap-2">
                <div class="min-w-0">
                    <h2 class="text-sm font-medium">{{ title }}</h2>
                    <p class="text-xs text-muted-foreground">
                        {{ profileNames.length }} 套配置{{ group.active ? `,已启用:${group.active}` : ',暂无启用' }}
                        (在「设置」页切换启用)
                    </p>
                </div>
                <div class="flex shrink-0 gap-2">
                    <Button variant="outline" :disabled="Boolean(testingName) || !group.active" @click="runTest()">
                        <Loader2 v-if="testingName && testingName === group.active" class="mr-1 h-4 w-4 animate-spin" />
                        {{ testingName && testingName === group.active ? '测试中…' : '测试启用配置' }}
                    </Button>
                    <Button @click="openCreate">
                        <Plus class="mr-1 h-4 w-4" /> 添加配置
                    </Button>
                </div>
            </div>

            <!-- 配置列表 -->
            <Table v-if="profileNames.length">
                <TableHeader>
                    <TableRow>
                        <TableHead>配置名</TableHead>
                        <TableHead>模型</TableHead>
                        <TableHead>Base URL</TableHead>
                        <TableHead>API Key</TableHead>
                        <TableHead class="text-right">操作</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    <template v-for="name in profileNames" :key="name">
                        <TableRow>
                            <TableCell class="font-medium">
                                {{ name }}
                                <span v-if="name === group.active"
                                    class="ml-1.5 rounded-full bg-emerald-100 px-1.5 py-0.5 text-xs text-emerald-700">
                                    启用中
                                </span>
                            </TableCell>
                            <TableCell>{{ group.profiles[name].model }}</TableCell>
                            <TableCell class="max-w-56 truncate text-muted-foreground"
                                :title="group.profiles[name].base_url">
                                {{ group.profiles[name].base_url }}
                            </TableCell>
                            <TableCell class="text-muted-foreground">
                                {{ group.profiles[name].api_key_configured ? '已配置' : '未配置' }}
                            </TableCell>
                            <TableCell class="text-right">
                                <div class="flex justify-end gap-1">
                                    <Button variant="ghost" size="icon" title="测试连接" :disabled="Boolean(testingName)"
                                        @click="runTest(name)">
                                        <Loader2 v-if="testingName === name" class="h-4 w-4 animate-spin" />
                                        <Activity v-else class="h-4 w-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon" title="编辑" @click="openEdit(name)">
                                        <Pencil class="h-4 w-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon" title="删除" :disabled="name === group.active"
                                        @click="askDelete(name)">
                                        <Trash2 class="h-4 w-4" />
                                    </Button>
                                </div>
                            </TableCell>
                        </TableRow>
                        <!-- 该配置条的连接测试结果:成功/失败就地展示 -->
                        <TableRow v-if="testResults[name]">
                            <TableCell :colspan="5" class="border-0 px-3 py-2 text-xs" :class="testResults[name].status === 'ok'
                                ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-destructive'">
                                <template v-if="testResults[name].status === 'ok'">
                                    <span class="flex flex-wrap items-center gap-x-2 gap-y-0.5 font-medium">
                                        <span class="flex items-center gap-1">
                                            <CircleCheck class="h-3.5 w-3.5" /> 连接成功
                                        </span>
                                        <span class="font-normal opacity-80">
                                            延迟 {{ formatDuration(testResults[name].latency_ms) }}
                                            <template v-if="testResults[name].dimension">
                                                · 向量维度 {{ testResults[name].dimension }}
                                            </template>
                                        </span>
                                    </span>
                                </template>
                                <span v-else class="flex items-center gap-1 font-medium">
                                    <CircleX class="h-3.5 w-3.5" /> 连接失败,请检查 Base URL、API Key 与 Model 配置后重试
                                </span>
                            </TableCell>
                        </TableRow>
                    </template>
                </TableBody>
            </Table>
            <EmptyState v-else :title="`暂无${title}配置`" description="点击右上角「添加配置」创建,首个配置将自动启用" />

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
                                placeholder="如 default、backup" @blur="touched = true" />
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
                            <Label for="pf-model">模型(下拉选择或手动输入)</Label>
                            <div class="flex gap-2">
                                <Input id="pf-model" v-model="form.model" placeholder="model-name 或点右侧拉取列表"
                                    @blur="touched = true" />
                                <Button variant="outline" class="shrink-0" :disabled="fetchingModels"
                                    @click="fetchModels">
                                    <Loader2 v-if="fetchingModels" class="mr-1 h-4 w-4 animate-spin" />
                                    {{ fetchingModels ? '拉取中…' : '拉取列表' }}
                                </Button>
                            </div>
                            <p v-if="touched && modelError" class="text-xs text-destructive">{{ modelError }}</p>
                            <!-- 拉取到的候选:点击回填到上方输入框(仍可手填) -->
                            <div v-if="modelOptions.length"
                                class="flex max-h-24 flex-wrap gap-1.5 overflow-y-auto pt-1">
                                <button v-for="m in modelOptions" :key="m" type="button"
                                    class="rounded-md border px-2 py-0.5 text-xs transition-colors hover:bg-accent"
                                    :class="form.model === m ? 'bg-accent font-medium' : 'text-muted-foreground'"
                                    @click="form.model = m">
                                    {{ m }}
                                </button>
                            </div>
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
    </div>
</template>
