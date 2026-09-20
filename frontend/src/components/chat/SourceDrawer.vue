<script setup lang="ts">
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerDescription,
  DrawerClose,
} from '@/components/ui/drawer'
import { FileText, X } from '@lucide/vue'

defineProps<{
  open: boolean
  source: {
    document_name?: string
    filename?: string
    page_start?: number
    page_end?: number
    section?: string
    content?: string
  } | null
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()
</script>

<template>
  <Drawer :open="open" @update:open="emit('update:open', $event)">
    <DrawerContent class="max-h-[80vh]">
      <DrawerHeader class="border-b border-border">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <FileText class="h-5 w-5 text-primary" />
            <div>
              <DrawerTitle class="text-sm font-semibold">
                {{ source?.document_name || source?.filename || '来源详情' }}
              </DrawerTitle>
              <DrawerDescription class="text-xs text-muted-foreground">
                <template v-if="source?.page_start">
                  第 {{ source.page_start }}<template v-if="source.page_end && source.page_end !== source.page_start">-{{ source.page_end }}</template> 页
                </template>
                <template v-if="source?.section"> · {{ source.section }}</template>
              </DrawerDescription>
            </div>
          </div>
          <DrawerClose class="p-1 rounded hover:bg-muted">
            <X class="h-4 w-4" />
          </DrawerClose>
        </div>
      </DrawerHeader>
      <div class="p-6 overflow-y-auto">
        <div
          v-if="source?.content"
          class="text-sm text-foreground leading-relaxed whitespace-pre-wrap bg-muted/30 rounded-lg p-4 border border-border"
        >
          {{ source.content }}
        </div>
        <div v-else class="text-sm text-muted-foreground text-center py-8">
          暂无内容
        </div>
      </div>
    </DrawerContent>
  </Drawer>
</template>
