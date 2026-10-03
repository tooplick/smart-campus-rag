<script setup lang="ts">
// 技术文档页:左侧目录(由内置 md 清单生成)+ 右侧 markdown-it 渲染区
// 内容源为前端内置 Markdown(import.meta.glob 静态导入),改文档需重新构建;纯前端无后端接口
import { computed, ref } from 'vue'
import { BookOpenText } from '@lucide/vue'
import { buildDocCatalog, findDoc } from '@/utils/docs'
import { renderMarkdown } from '@/utils/markdown'
import EmptyState from '@/components/common/EmptyState.vue'

const files = import.meta.glob('/src/docs/*.md', {
    eager: true,
    query: '?raw',
    import: 'default',
}) as Record<string, string>

const catalog = buildDocCatalog(files)
const activeSlug = ref<string | null>(catalog[0]?.slug ?? null)
const doc = computed(() => findDoc(catalog, activeSlug.value))
const html = computed(() => (doc.value ? renderMarkdown(doc.value.content) : ''))
</script>

<template>
    <div class="flex min-h-0 flex-1">
        <!-- 左侧目录 -->
        <aside class="w-52 shrink-0 overflow-y-auto border-r p-3">
            <p class="mb-2 px-2 text-xs font-medium text-muted-foreground">目录</p>
            <button v-for="d in catalog" :key="d.slug"
                class="block w-full rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent"
                :class="activeSlug === d.slug ? 'bg-accent font-medium' : 'text-muted-foreground'"
                @click="activeSlug = d.slug">
                {{ d.title }}
            </button>
        </aside>

        <!-- 右侧渲染区 -->
        <div class="min-w-0 flex-1 overflow-y-auto px-6 py-8">
            <EmptyState v-if="!doc" :icon="BookOpenText" title="暂无文档"
                description="在 frontend/src/docs/ 下添加 Markdown 文件后重新构建即可展示" />
            <!-- 文档内容为仓库内置的受控 markdown,无外部输入 -->
            <article v-else class="prose prose-sm dark:prose-invert mx-auto max-w-3xl" v-html="html" />
        </div>
    </div>
</template>
