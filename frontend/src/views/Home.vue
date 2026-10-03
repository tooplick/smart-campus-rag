<script setup lang="ts">
// 网站介绍页:Hero + 能力亮点 + 统计条(纯静态文案,本期不接公开统计接口)
import { BookOpen, FileText, MessageSquareQuote, Search, Sparkles } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

const features = [
    {
        icon: FileText,
        title: '多格式文档解析',
        desc: 'PDF / DOCX / PPTX / XLSX / CSV / 图片等统一解析入库,标题感知切块,支持四种切块模板。',
    },
    {
        icon: Search,
        title: '混合检索 + 重排',
        desc: '向量与关键词双路召回、加权融合、相似度过滤,可选重排模型精排,再经邻块扩展补全上下文。',
    },
    {
        icon: MessageSquareQuote,
        title: '来源引用溯源',
        desc: '回答中的 [来源 N] 角标对应检索到的原文切片,点击即可预览文档原文与页码。',
    },
]

const stats = [
    { value: '10+', label: '支持文档格式' },
    { value: '4', label: '切块模板' },
    { value: '2 路', label: '混合检索' },
    { value: '实时', label: 'SSE 流式回答' },
]
</script>

<template>
    <div class="min-h-full overflow-y-auto">
        <!-- Hero -->
        <section class="px-6 pb-12 pt-16 text-center">
            <p
                class="mb-3 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs text-muted-foreground">
                <Sparkles class="h-3.5 w-3.5" /> 智能校园知识库问答系统
            </p>
            <h1 class="mx-auto max-w-2xl text-3xl font-bold tracking-tight md:text-4xl">
                用自然语言,秒查校园文档
            </h1>
            <p class="mx-auto mt-4 max-w-xl text-muted-foreground">
                上传校园制度、手册与通知,系统自动解析入库;提问即得带来源引用的准确回答。
            </p>
            <div class="mt-7 flex justify-center gap-3">
                <Button size="lg" @click="$router.push('/chat')">开始提问</Button>
                <Button size="lg" variant="outline" @click="$router.push('/docs')">查看文档</Button>
            </div>
        </section>

        <!-- 能力亮点 -->
        <section class="mx-auto grid max-w-5xl gap-4 px-6 md:grid-cols-3">
            <Card v-for="f in features" :key="f.title" class="bg-background">
                <CardContent class="space-y-2.5 p-5">
                    <component :is="f.icon" class="h-6 w-6 text-primary" />
                    <h2 class="font-semibold">{{ f.title }}</h2>
                    <p class="text-sm leading-relaxed text-muted-foreground">{{ f.desc }}</p>
                </CardContent>
            </Card>
        </section>

        <!-- 统计条(静态文案) -->
        <section class="mx-auto mt-12 max-w-5xl px-6 pb-16">
            <div class="grid grid-cols-2 gap-4 rounded-xl border bg-muted/40 p-6 md:grid-cols-4">
                <div v-for="s in stats" :key="s.label" class="text-center">
                    <p class="text-2xl font-semibold">{{ s.value }}</p>
                    <p class="mt-1 text-sm text-muted-foreground">{{ s.label }}</p>
                </div>
            </div>
            <p class="mt-6 text-center text-sm text-muted-foreground">
                <BookOpen class="mr-1.5 inline h-4 w-4" />
                管理员可在后台维护知识库与文档,回答效果即刻生效
            </p>
        </section>
    </div>
</template>
