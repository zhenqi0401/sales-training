<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const phone = ref('')
const code = ref('')
const sending = ref(false)
const countdown = ref(0)
const agree = ref(true)
const loading = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

function isPhoneValid() {
  return /^1[3-9]\d{9}$/.test(phone.value)
}

function startCountdown() {
  countdown.value = 60
  sending.value = true
  timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      sending.value = false
      if (timer) clearInterval(timer)
    }
  }, 1000)
}

async function sendCode() {
  if (!isPhoneValid()) {
    showToast('请输入正确的手机号')
    return
  }
  try {
    await authApi.sendCode(phone.value)
    showToast('验证码已发送')
    startCountdown()
  } catch (e: any) {
    showToast(e?.response?.data?.detail || e?.message || '发送失败，请重试')
  }
}

function isValid() {
  if (!isPhoneValid()) {
    showToast('请输入正确的手机号')
    return false
  }
  if (!code.value || code.value.length < 4) {
    showToast('请输入验证码')
    return false
  }
  if (!agree.value) {
    showToast('请同意用户协议')
    return false
  }
  return true
}

async function handleLogin() {
  if (!isValid()) return
  loading.value = true
  showLoadingToast({
    message: '登录中...',
    forbidClick: true,
    duration: 0
  })
  try {
    const user = await authStore.login(phone.value, code.value)
    closeToast()
    showToast('登录成功')
    const redirect = (route.query.redirect as string) || '/home'
    router.replace(user.mustChangePassword ? '/init-password' : redirect)
  } catch (e: any) {
    closeToast()
    showToast(e?.response?.data?.detail || e?.message || '登录失败')
  } finally {
    loading.value = false
  }
}

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="login-page">
    <div class="login-header bg-gradient-primary">
      <div class="header-content">
        <h1 class="logo-text">眼视光销售培训</h1>
        <p class="logo-subtitle">专业销售技能提升平台</p>
      </div>
    </div>

    <div class="login-form">
      <h2 class="form-title">手机号登录</h2>

      <van-form @submit="handleLogin">
        <van-cell-group inset>
          <van-field
            v-model="phone"
            label="手机号"
            type="tel"
            maxlength="11"
            placeholder="请输入手机号"
            :rules="[{ pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号' }]"
          >
            <template #button>
              <van-button
                round
                size="small"
                :disabled="sending"
                @click="sendCode"
                color="linear-gradient(135deg, var(--primary), var(--primary-dark))"
              >
                {{ sending ? `${countdown}s` : '获取验证码' }}
              </van-button>
            </template>
          </van-field>

          <van-field
            v-model="code"
            label="验证码"
            type="digit"
            maxlength="6"
            placeholder="请输入验证码"
            :rules="[{ required: true, message: '请输入验证码' }]"
          />
        </van-cell-group>

        <div class="agreement">
          <van-checkbox v-model="agree" shape="round" icon-size="14">
            <span class="agree-text">登录即表示同意</span>
            <span class="agree-link">《用户协议》</span>
            <span class="agree-text">和</span>
            <span class="agree-link">《隐私政策》</span>
          </van-checkbox>
        </div>

        <div class="login-button-wrap">
          <van-button
            round
            block
            type="primary"
            native-type="submit"
            :loading="loading"
            color="linear-gradient(135deg, var(--primary), var(--primary-dark))"
            size="large"
          >
            登录
          </van-button>
        </div>
      </van-form>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  background: $bg;
}

.login-header {
  padding: 48px 30px 36px;
  text-align: center;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 40%, rgba(255,255,255,0.15) 0%, transparent 60%);
  }
}

.header-content {
  position: relative;
  z-index: 1;
}

.logo-text {
  color: #fff;
  font-size: 26px;
  font-weight: 700;
  margin-bottom: 8px;
}

.logo-subtitle {
  color: rgba(255, 255, 255, 0.85);
  font-size: 14px;
}

.login-form {
  margin-top: -20px;
  position: relative;
  z-index: 2;
}

.form-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  padding: 20px 24px 16px;
}

.agreement {
  padding: 16px 24px 0;
}

.agree-text {
  font-size: 12px;
  color: var(--text-muted);
}

.agree-link {
  font-size: 12px;
  color: var(--primary);
}

.login-button-wrap {
  padding: 24px 16px;
}
</style>
