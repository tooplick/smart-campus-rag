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
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  if (!username.value || !password.value) return
  error.value = ''
  loading.value = true
  try {
    const res = await authStore.login(username.value, password.value)
    if (res.success) {
      if (authStore.mustChangePassword) {
        router.push('/admin/initialize')
      } else {
        router.push('/admin/dashboard')
      }
    } else {
      error.value = res.message || '用户名或密码错误'
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
        <h1 class="text-xl font-bold text-foreground">智能校园知识库</h1>
        <p class="text-sm text-muted-foreground mt-1">管理后台</p>
      </div>
      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-foreground mb-1.5">用户名</label>
          <div class="relative">
            <User class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              v-model="username"
              type="text"
              class="pl-10"
              placeholder="请输入用户名"
            />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-foreground mb-1.5">密码</label>
          <div class="relative">
            <Lock class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              v-model="password"
              type="password"
              class="pl-10"
              placeholder="请输入密码"
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
          {{ loading ? '登录中...' : '登录' }}
        </Button>
      </form>
    </div>
  </div>
</template>
