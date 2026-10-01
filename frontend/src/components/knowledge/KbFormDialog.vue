<script setup lang="ts">
import { reactive, watch } from 'vue'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { KnowledgeBase } from '@/api/types'

const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{ editing?: KnowledgeBase | null }>()
const emit = defineEmits<{ save: [body: { name: string; description?: string; icon?: string; chunk_template?: string }] }>()

const form = reactive({ name: '', description: '', icon: '', chunk_template: 'general' })

/** 切块模板选项(对齐 RAGFlow 模板化切块) */
const templateOptions = [
  { value: 'general', label: '通用(句级流式切块)' },
  { value: 'section', label: '章节(按章节独立切块)' },
  { value: 'qa', label: '问答对(Q/A 成对成块)' },
  { value: 'one', label: '整篇(短文档单切片)' },
]

/** 打开对话框时按编辑对象回填表单 */
watch(open, (v) => {
  if (v) {
    form.name = props.editing?.name ?? ''
    form.description = props.editing?.description ?? ''
    form.icon = props.editing?.icon ?? ''
    form.chunk_template = props.editing?.chunk_template ?? 'general'
  }
})

/** 校验名称非空后抛出 save 事件并关闭 */
function submit() {
  if (!form.name.trim()) return
  emit('save', {
    name: form.name.trim(),
    description: form.description.trim() || undefined,
    icon: form.icon.trim() || undefined,
    chunk_template: form.chunk_template,
  })
  open.value = false
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ editing ? '编辑知识库' : '新建知识库' }}</DialogTitle>
      </DialogHeader>
      <div class="space-y-4">
        <div class="space-y-2">
          <Label for="kb-name">名称</Label>
          <Input id="kb-name" v-model="form.name" required />
        </div>
        <div class="space-y-2">
          <Label for="kb-desc">描述</Label>
          <Textarea id="kb-desc" v-model="form.description" :rows="3" />
        </div>
        <div class="space-y-2">
          <Label for="kb-icon">图标(可选)</Label>
          <Input id="kb-icon" v-model="form.icon" />
        </div>
        <div class="space-y-2">
          <Label>切块模板</Label>
          <Select v-model="form.chunk_template">
            <SelectTrigger class="w-full">
              <SelectValue placeholder="选择切块模板" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="opt in templateOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </SelectItem>
            </SelectContent>
          </Select>
          <p class="text-xs text-muted-foreground">按资料形态选择;对新上传与重新处理的文档生效</p>
        </div>
      </div>
      <DialogFooter>
        <Button variant="outline" @click="open = false">取消</Button>
        <Button @click="submit">保存</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
