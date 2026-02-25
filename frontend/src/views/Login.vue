<script setup>
/**
 * 登录/注册页面，登录和注册共用一个表单，通过 isRegister 切换。
 * 登录成功后会跳回之前要去的页面（如果有 redirect 参数的话）。
 */
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const isRegister = ref(false)
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
  nickname: '',
})

async function handleSubmit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    if (isRegister.value) {
      await authStore.register(form.username, form.password, form.nickname)
      ElMessage.success('注册成功')
    } else {
      await authStore.login(form.username, form.password)
      ElMessage.success('登录成功')
    }
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch (err) {
    // 错误已经被 axios 拦截器处理并弹出提示了，这里不用再做什么
  } finally {
    loading.value = false
  }
}

function toggleMode() {
  isRegister.value = !isRegister.value
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-title">深圳交通速度分析系统</div>
      <div class="login-subtitle">{{ isRegister ? '创建新账号' : '欢迎回来，请登录' }}</div>

      <el-form @submit.prevent="handleSubmit" label-position="top" @keyup.enter="handleSubmit">
        <el-form-item label="用户名">
          <el-input
            v-model="form.username"
            prefix-icon="User"
            placeholder="请输入用户名"
            size="large"
          />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            prefix-icon="Lock"
            placeholder="请输入密码"
            show-password
            size="large"
          />
        </el-form-item>
        <el-form-item v-if="isRegister" label="昵称（选填）">
          <el-input
            v-model="form.nickname"
            prefix-icon="UserFilled"
            placeholder="请输入昵称"
            size="large"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            @click="handleSubmit"
            :loading="loading"
            size="large"
            style="width: 100%;"
          >
            {{ isRegister ? '注册' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div style="text-align: center;">
        <el-button text type="primary" @click="toggleMode">
          {{ isRegister ? '已有账号？去登录' : '没有账号？去注册' }}
        </el-button>
      </div>
    </div>
  </div>
</template>
