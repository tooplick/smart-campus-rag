<script setup lang="ts">
import { ref } from 'vue'
import { toast } from 'vue-sonner'
import { uploadDocument } from '@/api/documents'
import { errorMessage } from '@/utils/request'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{ knowledgeBaseId: number | null }>()
const emit = defineEmits<{ uploaded: [] }>()

const files = ref<File[]>([])
const uploading = ref(false)

/** 读取多选文件 */
function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  files.value = Array.from(input.files ?? [])
}

/** 逐个上传选中文件,完成后通知父组件刷新 */
async function submit() {
  if (!props.knowledgeBaseId) return toast.error('请先选择知识库')
  if (!files.value.length) return toast.error('请选择文件')
  uploading.value = true
  let ok = 0
  for (const f of files.value) {
    try {
      await uploadDocument(props.knowledgeBaseId, f)
      ok++
    } catch (e) {
      toast.error(`${f.name}:${errorMessage(e)}`)
    }
  }
  uploading.value = false
  if (ok > 0) toast.success(`已上传 ${ok} 个文件`)
  files.value = []
  open.value = false
  emit('uploaded')
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>上传文档</DialogTitle>
      </DialogHeader>
      <input
        type="file" multiple accept=".pdf,.docx,.txt,.md,.csv,.xlsx,.pptx,.html,.htm,.png,.jpg,.jpeg"
        class="block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-accent file:px-3 file:py-1.5 file:text-sm"
        @change="onFileChange"
      />
      <p v-if="files.length" class="text-sm text-muted-foreground">已选 {{ files.length }} 个文件</p>
      <p v-else class="text-sm text-muted-foreground">支持 PDF / Word / TXT / Markdown / CSV / Excel / PPT / HTML / 图片,可多选</p>
      <DialogFooter>
        <Button variant="outline" @click="open = false">取消</Button>
        <Button :disabled="uploading" @click="submit">{{ uploading ? '上传中…' : '上传' }}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
