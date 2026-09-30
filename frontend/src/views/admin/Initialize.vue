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
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)

/** 首次初始化:校验新密码后提交并进入仪表盘 */
async function submit() {
  if (newPassword.value.length < 6) return toast.error('新密码长度至少 6 位')
  if (newPassword.value !== confirmPassword.value) return toast.error('两次输入的新密码不一致')
  loading.value = true
  try {
    await auth.initialize(username.value, currentPassword.value, newPassword.value)
    toast.success('初始化成功')
    router.push('/admin/dashboard')
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
      <h1 class="text-xl font-semibold">首次初始化</h1>
      <p class="text-sm text-muted-foreground">首次登录需修改默认密码</p>
      <div class="space-y-2">
        <Label for="username">用户名</Label>
        <Input id="username" v-model="username" required />
      </div>
      <div class="space-y-2">
        <Label for="current">当前密码</Label>
        <Input id="current" v-model="currentPassword" type="password" required />
      </div>
      <div class="space-y-2">
        <Label for="new">新密码(至少 6 位)</Label>
        <Input id="new" v-model="newPassword" type="password" required />
      </div>
      <div class="space-y-2">
        <Label for="confirm">确认新密码</Label>
        <Input id="confirm" v-model="confirmPassword" type="password" required />
      </div>
      <Button class="w-full" :disabled="loading">{{ loading ? '提交中…' : '完成初始化' }}</Button>
    </form>
  </div>
</template>
