<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <h1>销售培训系统</h1>
        <p>管理后台</p>
      </div>

      <el-form class="login-form" @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="username" placeholder="用户名" size="large" />
        </el-form-item>

        <el-form-item>
          <el-input v-model="password" type="password" placeholder="密码" size="large" show-password @keyup.enter="handleLogin" />
        </el-form-item>

        <el-form-item>
          <div class="captcha-row">
            <el-input v-model="captchaInput" placeholder="验证码" size="large" class="captcha-input" @keyup.enter="handleLogin" />
            <div class="captcha-img" @click="refreshCaptcha" v-html="captchaSvg"></div>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" size="large" class="login-btn" :loading="loading" @click="handleLogin">
            {{ loading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer"><span>v1.0</span></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const username = ref('admin')
const password = ref('admin123')
const captchaInput = ref('')
const captchaCode = ref('')
const captchaSvg = ref('')
const loading = ref(false)

function generateCaptcha() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  let code = ''
  for (let i = 0; i < 4; i++) code += chars[Math.floor(Math.random() * chars.length)]
  captchaCode.value = code

  const W = 120, H = 40
  const colors = ['#1e40af', '#92400e', '#065f46', '#7c3aed', '#be123c', '#0e7490']
  let extra = ''
  for (let i = 0; i < 6; i++) extra += `<line x1="${Math.random() * W}" y1="${Math.random() * H}" x2="${Math.random() * W}" y2="${Math.random() * H}" stroke="#e2e8f0" stroke-width="${0.5 + Math.random() * 1.5}"/>`
  for (let i = 0; i < 20; i++) extra += `<circle cx="${Math.random() * W}" cy="${Math.random() * H}" r="${0.5 + Math.random() * 1.5}" fill="#94a3b8" opacity="0.5"/>`
  let texts = ''
  for (let i = 0; i < code.length; i++) {
    const c = colors[Math.floor(Math.random() * colors.length)]
    texts += `<text x="${14 + i * 26 + (Math.random() - 0.5) * 6}" y="${28 + (Math.random() - 0.5) * 8}" font-size="22" font-weight="bold" fill="${c}" transform="rotate(${(Math.random() - 0.5) * 30}, ${14 + i * 26}, 28)" font-family="Arial">${code[i]}</text>`
  }
  captchaSvg.value = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}"><rect width="${W}" height="${H}" fill="#f8fafc" rx="4"/><rect width="${W}" height="${H}" fill="none" stroke="#e2e8f0" stroke-width="1" rx="4"/>${extra}${texts}</svg>`
}

function refreshCaptcha() {
  generateCaptcha()
  captchaInput.value = ''
}

async function handleLogin() {
  if (captchaInput.value.toLowerCase() !== captchaCode.value.toLowerCase()) {
    ElMessage.error('验证码错误')
    refreshCaptcha()
    return
  }
  if (!username.value || !password.value) {
    ElMessage.error('请输入用户名和密码')
    return
  }

  loading.value = true
  try {
    await authStore.login(username.value, password.value)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '登录失败'
    ElMessage.error(msg)
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}

onMounted(() => generateCaptcha())
</script>

<style scoped lang="scss">
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-container {
  width: 420px;
  padding: 40px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}
.login-header {
  text-align: center;
  margin-bottom: 32px;
  h1 { font-size: 24px; font-weight: 700; color: #303133; margin: 0 0 4px; }
  p { font-size: 14px; color: #909399; margin: 0; }
}
.login-form {
  .captcha-row { display: flex; gap: 12px;
    .captcha-input { flex: 1; }
    .captcha-img { width: 120px; height: 40px; border-radius: 6px; cursor: pointer; flex-shrink: 0; overflow: hidden; border: 1px solid #e2e8f0;
      &:hover { opacity: 0.8; }
    }
  }
  .login-btn { width: 100%; font-size: 16px; height: 44px; }
}
.login-footer { text-align: center; margin-top: 24px; font-size: 12px; color: #c0c4cc; }
</style>
