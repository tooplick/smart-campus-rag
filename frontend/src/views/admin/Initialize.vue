<script setup lang="ts">
// 首次初始化改密:新密码长度与两次一致性即时校验(内联红字),密码均可切换显隐
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { Eye, EyeOff, Loader2, ShieldCheck } from '@lucide/vue'
import { useAuthStore } from '@/stores/auth'
import { errorMessage } from '@/utils/request'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import FieldError from '@/components/common/FieldError.vue'

const router = useRouter()
const auth = useAuthStore()

const username = ref('admin')
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const showPassword = reactive({ current: false, next: false, confirm: false })
const loading = ref(false)
// touched:失焦后才展示该字段的内联错误
const touched = reactive({ current: false, next: false, confirm: false })

const currentError = computed(() => (currentPassword.value ? '' : '请输入当前密码'))
const newError = computed(() => {
  if (!newPassword.value) return '请输入新密码'
  if (newPassword.value.length < 6) return '新密码长度至少 6 位'
  return ''
})
const confirmError = computed(() => {
  if (!confirmPassword.value) return '请再次输入新密码'
  if (confirmPassword.value !== newPassword.value) return '两次输入的新密码不一致'
  return ''
})

/** 首次初始化:全部字段校验通过后提交并进入仪表盘 */
async function submit() {
  touched.current = touched.next = touched.confirm = true
  // 校验不通过:首条错误顶部居中 toast 弹出(字段行内红字同步标出)
  if (currentError.value || newError.value || confirmError.value) {
    toast.error(currentError.value || newError.value || confirmError.value)
    return
  }
  loading.value = true
  try {
    await auth.initialize(username.value, currentPassword.value, newPassword.value)
    toast.success('初始化成功')
    router.push('/Dashboard')
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-full flex-1 items-center justify-center overflow-y-auto bg-muted/40 p-4">
    <form class="w-full max-w-sm space-y-4 rounded-xl border bg-background p-6 shadow-lg" @submit.prevent="submit">
      <div>
        <h1 class="flex items-center gap-2 text-xl font-semibold">
          <ShieldCheck class="h-5 w-5" /> 首次初始化
        </h1>
        <p class="mt-1 text-sm text-muted-foreground">首次登录需修改默认密码</p>
      </div>
      <div class="space-y-1">
        <Label for="username">用户名</Label>
        <Input id="username" v-model="username" autocomplete="username" required />
      </div>
      <div class="space-y-1">
        <Label for="current">当前密码</Label>
        <div class="relative">
          <Input id="current" v-model="currentPassword" :type="showPassword.current ? 'text' : 'password'" class="pr-10"
            autocomplete="current-password" required :aria-invalid="Boolean(touched.current && currentError)"
            @blur="touched.current = true" />
          <button type="button"
            class="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:text-foreground"
            :aria-label="showPassword.current ? '隐藏密码' : '显示密码'" @click="showPassword.current = !showPassword.current">
            <EyeOff v-if="showPassword.current" class="h-4 w-4" />
            <Eye v-else class="h-4 w-4" />
          </button>
        </div>
        <FieldError :message="touched.current ? currentError : ''" />
      </div>
      <div class="space-y-1">
        <Label for="new">新密码(至少 6 位)</Label>
        <div class="relative">
          <Input id="new" v-model="newPassword" :type="showPassword.next ? 'text' : 'password'" class="pr-10"
            autocomplete="new-password" required :aria-invalid="Boolean(touched.next && newError)"
            @blur="touched.next = true" />
          <button type="button"
            class="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:text-foreground"
            :aria-label="showPassword.next ? '隐藏密码' : '显示密码'" @click="showPassword.next = !showPassword.next">
            <EyeOff v-if="showPassword.next" class="h-4 w-4" />
            <Eye v-else class="h-4 w-4" />
          </button>
        </div>
        <FieldError :message="touched.next ? newError : ''" />
      </div>
      <div class="space-y-1">
        <Label for="confirm">确认新密码</Label>
        <div class="relative">
          <Input id="confirm" v-model="confirmPassword" :type="showPassword.confirm ? 'text' : 'password'" class="pr-10"
            autocomplete="new-password" required :aria-invalid="Boolean(touched.confirm && confirmError)"
            @blur="touched.confirm = true" />
          <button type="button"
            class="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:text-foreground"
            :aria-label="showPassword.confirm ? '隐藏密码' : '显示密码'" @click="showPassword.confirm = !showPassword.confirm">
            <EyeOff v-if="showPassword.confirm" class="h-4 w-4" />
            <Eye v-else class="h-4 w-4" />
          </button>
        </div>
        <!-- 确认密码的不一致提示即时联动新密码修改 -->
        <FieldError :message="touched.confirm || confirmPassword ? confirmError : ''" />
      </div>
      <Button class="w-full" :disabled="loading">
        <Loader2 v-if="loading" class="mr-1 h-4 w-4 animate-spin" />
        {{ loading ? '提交中…' : '完成初始化' }}
      </Button>
    </form>
  </div>
</template>
