<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import { Lock, User } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)

async function handleInitialize() {
  if (!currentPassword.value || !newPassword.value || !confirmPassword.value) return
  if (newPassword.value !== confirmPassword.value) {
    error.value = '两次密码不一致'
    return
  }
  error.value = ''
  loading.value = true
  try {
    const res = await authStore.initialize(
      username.value || authStore.admin?.username || 'admin',
      currentPassword.value,
      newPassword.value
    )
    if (res.success) {
      router.push('/admin/dashboard')
    } else {
      error.value = res.message || '初始化失败'
    }
  } catch (e: any) {
    error.value = e?.message || '服务暂时不可用'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-muted/30">
    <div class="w-full max-w-sm rounded-xl bg-card p-8 shadow-sm border border-border">
      <div class="text-center mb-8">
        <h1 class="text-xl font-bold text-foreground">设置管理员账号</h1>
        <p class="text-sm text-muted-foreground mt-1">首次登录请修改密码</p>
      </div>
      <form @submit.prevent="handleInitialize" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-foreground mb-1.5">当前密码</label>
          <div class="relative">
            <Lock class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              v-model="currentPassword"
              type="password"
              class="pl-10"
              placeholder="请输入当前密码"
            />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-foreground mb-1.5">新用户名</label>
          <div class="relative">
            <User class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              v-model="username"
              type="text"
              class="pl-10"
              :placeholder="authStore.admin?.username || 'admin'"
            />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-foreground mb-1.5">新密码</label>
          <div class="relative">
            <Lock class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              v-model="newPassword"
              type="password"
              class="pl-10"
              placeholder="请输入新密码"
            />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-foreground mb-1.5">确认密码</label>
          <div class="relative">
            <Lock class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              v-model="confirmPassword"
              type="password"
              class="pl-10"
              placeholder="再次输入密码"
            />
          </div>
        </div>
        <div v-if="error" class="text-sm text-destructive text-center">
          {{ error }}
        </div>
        <Button
          type="submit"
          :disabled="loading"
          class="w-full"
        >
          {{ loading ? '提交中...' : '完成初始化' }}
        </Button>
      </form>
    </div>
  </div>
</template>
