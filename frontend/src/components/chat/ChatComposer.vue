<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { Plus, SendHorizonal } from '@lucide/vue'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

const props = defineProps<{ disabled?: boolean }>()
const emit = defineEmits<{ send: [content: string] }>()

const text = ref('')
const MAX = 2000
/** 输入区最大高度(px),到顶后内部滚动 */
const MAX_HEIGHT = 200
const inputWrap = ref<HTMLElement | null>(null)

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    submit()
  }
}

/** 输入后自适应高度:随内容平滑增高/回缩到上限,发送/清空后复位。
 *  关键:height 过渡进行中,生效高度是动画中途值,压到 0 后立刻测会被旧高钳住
 *  (scrollHeight ≥ clientHeight)导致不回缩——所以测量必须先关过渡让高度瞬变,
 *  测完恢复过渡并从旧高一次性动画到目标高;全程保存/恢复 scrollTop 保持光标跟随。 */
function autoGrow() {
  const el = inputWrap.value?.querySelector('textarea')
  if (!el) return
  const scrollTop = el.scrollTop
  const oldHeight = el.clientHeight

  // 关过渡 → 压到 0 → 测出真实内容高(瞬时生效,不受动画钳制)
  el.style.transition = 'none'
  el.style.height = '0px'
  const contentHeight = el.scrollHeight
  const fit = Math.min(contentHeight, MAX_HEIGHT)
  // 仅当内容真正超出上限才显示滚动条:增高动画途中框高小于内容,
  // 若平时为 auto 会在此刻闪现滚动条
  el.style.overflowY = contentHeight > MAX_HEIGHT ? 'auto' : 'hidden'

  // 拉回旧高并提交,恢复过渡,再写目标高:旧→新 一次性平滑动画
  el.style.height = `${oldHeight}px`
  void el.offsetHeight
  el.style.transition = ''
  el.style.height = `${fit}px`
  el.scrollTop = scrollTop
}

// 挂载时即写入 px 基线,避免首次增高 auto→px 无过渡
onMounted(() => autoGrow())

/** 附件入口暂未开放 */
function onAttach() {
  toast.info('附件功能暂未开放')
}

function submit() {
  const content = text.value.trim()
  if (!content || content.length > MAX || props.disabled) return
  emit('send', content)
  text.value = ''
  nextTick(autoGrow)
}
</script>

<template>
  <div class="px-4 pb-6 pt-2">
    <div class="mx-auto max-w-3xl">
      <!-- ChatGPT 风格胶囊悬浮容器:静止时端头正半圆(28px),增高后固定弧度;+/发送钮钉在左下/右下角,不随增高移动 -->
      <div class="flex items-end gap-2 rounded-[28px] border bg-background p-2 shadow-lg transition-shadow focus-within:shadow-xl">
        <Button
          variant="ghost"
          size="icon"
          class="mb-1 shrink-0 self-end rounded-full text-muted-foreground"
          aria-label="添加附件"
          @click="onAttach"
        >
          <Plus />
        </Button>
        <div ref="inputWrap" class="relative flex-1">
          <Textarea
            v-model="text" :rows="1" :maxlength="MAX" placeholder="请输入你的问题"
            class="max-h-[200px] min-h-10 w-full resize-none border-0 bg-transparent px-0 pr-12 shadow-none focus-visible:ring-0 dark:bg-transparent"
            @keydown="onKeydown" @input="autoGrow"
          />
          <!-- 发送按钮钉在右下角(增高时不移动);滚动条贴输入区右缘,位于按钮右侧 -->
          <Button
            size="icon"
            class="absolute bottom-1 right-3 rounded-full"
            :disabled="disabled || !text.trim()"
            @click="submit"
          >
            <SendHorizonal class="h-4 w-4" />
          </Button>
        </div>
      </div>
      <p class="mt-1.5 pr-2 text-right text-xs text-muted-foreground">{{ text.length }}/{{ MAX }}</p>
    </div>
  </div>
</template>

<style scoped>
/* 输入区:高度平滑过渡 + 关闭原生 field-sizing 由 JS 接管 + 到顶后的细滚动条 */
:deep(textarea) {
  transition: height 150ms ease-out;
  field-sizing: fixed;
  scrollbar-width: thin;
  scrollbar-color: color-mix(in oklab, currentColor 30%, transparent) transparent;
}

/* 细滚动条(Chrome/Edge) */
:deep(textarea)::-webkit-scrollbar {
  width: 6px;
}
:deep(textarea)::-webkit-scrollbar-track {
  background: transparent;
}
:deep(textarea)::-webkit-scrollbar-thumb {
  background: color-mix(in oklab, currentColor 30%, transparent);
  border-radius: 9999px;
}
:deep(textarea)::-webkit-scrollbar-thumb:hover {
  background: color-mix(in oklab, currentColor 45%, transparent);
}
</style>
