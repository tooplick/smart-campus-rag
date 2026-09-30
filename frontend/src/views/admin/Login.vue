<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { useAuthStore } from '@/stores/auth'
import { errorMessage } from '@/utils/request'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const router = useRouter()
const auth = useAuthStore()

const username = ref('admin')
const password = ref('')
const loading = ref(false)

/** 提交登录,按是否需改密跳转初始化页或仪表盘 */
async function submit() {
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push(auth.mustChangePassword ? '/admin/initialize' : '/admin/dashboard')
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-muted/40">
    <form class="w-80 space-y-4 rounded-lg border bg-background p-6" @submit.prevent="submit">
      <h1 class="text-xl font-semibold">管理后台登录</h1>
      <div class="space-y-2">
        <Label for="username">用户名</Label>
        <Input id="username" v-model="username" autocomplete="username" required />
      </div>
      <div class="space-y-2">
        <Label for="password">密码</Label>
        <Input id="password" v-model="password" type="password" autocomplete="current-password" required />
      </div>
      <Button class="w-full" :disabled="loading">{{ loading ? '登录中…' : '登录' }}</Button>
    </form>
  </div>
</template>
