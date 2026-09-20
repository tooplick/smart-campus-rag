<script setup lang="ts">
import CitationCard from './CitationCard.vue'

defineProps<{
  citations: Array<any>
}>()

const emit = defineEmits<{
  'view-source': [citation: any]
}>()
</script>

<template>
  <div v-if="citations.length > 0" class="mt-3 pt-3 border-t border-border/50">
    <div class="text-xs text-muted-foreground mb-2">来源引用</div>
    <div class="grid gap-1.5">
      <CitationCard
        v-for="(c, i) in citations"
        :key="i"
        :citation="c"
        :index="i + 1"
        @view="emit('view-source', $event)"
      />
    </div>
  </div>
</template>
