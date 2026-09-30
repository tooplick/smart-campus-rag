<script setup lang="ts">
import { reactive, watch } from 'vue'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { KnowledgeBase } from '@/api/types'

const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{ editing?: KnowledgeBase | null }>()
const emit = defineEmits<{ save: [body: { name: string; description?: string; icon?: string }] }>()

const form = reactive({ name: '', description: '', icon: '' })

/** 打开对话框时按编辑对象回填表单 */
watch(open, (v) => {
  if (v) {
    form.name = props.editing?.name ?? ''
    form.description = props.editing?.description ?? ''
    form.icon = props.editing?.icon ?? ''
  }
})

/** 校验名称非空后抛出 save 事件并关闭 */
function submit() {
  if (!form.name.trim()) return
  emit('save', {
    name: form.name.trim(),
    description: form.description.trim() || undefined,
    icon: form.icon.trim() || undefined,
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
      </div>
      <DialogFooter>
        <Button variant="outline" @click="open = false">取消</Button>
        <Button @click="submit">保存</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
