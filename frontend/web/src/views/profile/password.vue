<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance } from 'element-plus'
import { changeOwnPassword } from '@/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const formRef = ref<FormInstance>()
const form = ref({ oldPassword: '', newPassword: '', confirm: '' })

const rules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [{ required: true, min: 6, message: '新密码至少 6 位', trigger: 'blur' }],
  confirm: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: (_r: unknown, v: string, cb: (e?: Error) => void) => v === form.value.newPassword ? cb() : cb(new Error('两次密码不一致')), trigger: 'blur' },
  ],
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  await changeOwnPassword(form.value.oldPassword, form.value.newPassword)
  ElMessage.success('修改成功，请重新登录')
  auth.reset()
  router.push('/login')
}
</script>

<template>
  <div class="pw-page">
    <el-card style="max-width: 480px">
      <template #header>修改密码</template>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="原密码" prop="oldPassword"><el-input v-model="form.oldPassword" type="password" show-password /></el-form-item>
        <el-form-item label="新密码" prop="newPassword"><el-input v-model="form.newPassword" type="password" show-password /></el-form-item>
        <el-form-item label="确认密码" prop="confirm"><el-input v-model="form.confirm" type="password" show-password /></el-form-item>
        <el-form-item><el-button type="primary" @click="submit">确定</el-button></el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.pw-page { padding: 24px; }
</style>
