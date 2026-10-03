<script setup lang="ts">
// 管理后台登录:校验内联到字段,密码可切换显隐;登录后按 must_change_password 分流
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { Eye, EyeOff, Loader2, LogIn } from '@lucide/vue'
import { useAuthStore } from '@/stores/auth'
import { errorMessage } from '@/utils/request'
import { safeRedirect } from '@/utils/guard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import FieldError from '@/components/common/FieldError.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const username = ref('admin')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
// touched:失焦后才展示该字段的内联错误,避免一进页面就标红
const touched = reactive({ username: false, password: false })

const usernameError = computed(() => (username.value.trim() ? '' : '请输入用户名'))
const passwordError = computed(() => (password.value ? '' : '请输入密码'))

/** 提交登录:强制改密进初始化页;否则回 redirect 原页,无则进仪表盘 */
async function submit() {
  touched.username = true
  touched.password = true
  if (usernameError.value || passwordError.value) return
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    if (auth.mustChangePassword) router.push('/Initialize')
    else router.push(safeRedirect(route.query.redirect) ?? '/Dashboard')
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
          <LogIn class="h-5 w-5" /> 管理后台登录
        </h1>
        <p class="mt-1 text-sm text-muted-foreground">智能校园知识库管理控制台</p>
      </div>
      <div class="space-y-1">
        <Label for="username">用户名</Label>
        <Input id="username" v-model="username" autocomplete="username" required
          :aria-invalid="Boolean(touched.username && usernameError)" @blur="touched.username = true" />
        <FieldError :message="touched.username ? usernameError : ''" />
      </div>
      <div class="space-y-1">
        <Label for="password">密码</Label>
        <!-- 密码显隐切换:切换按钮钉在输入框右端 -->
        <div class="relative">
          <Input id="password" v-model="password" :type="showPassword ? 'text' : 'password'" class="pr-10"
            autocomplete="current-password" required :aria-invalid="Boolean(touched.password && passwordError)"
            @blur="touched.password = true" />
          <button type="button"
            class="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:text-foreground"
            :aria-label="showPassword ? '隐藏密码' : '显示密码'" @click="showPassword = !showPassword">
            <EyeOff v-if="showPassword" class="h-4 w-4" />
            <Eye v-else class="h-4 w-4" />
          </button>
        </div>
        <FieldError :message="touched.password ? passwordError : ''" />
      </div>
      <Button class="w-full" :disabled="loading">
        <Loader2 v-if="loading" class="mr-1 h-4 w-4 animate-spin" />
        {{ loading ? '登录中…' : '登录' }}
      </Button>
    </form>
  </div>
</template>
