<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const phone = ref('')
const password = ref('')
const loading = ref(false)

function isPhoneValid() {
  return /^1[3-9]\d{9}$/.test(phone.value)
}

function isValid() {
  if (!isPhoneValid()) {
    showToast('请输入正确的手机号')
    return false
  }
  if (!password.value || password.value.length < 6) {
    showToast('请输入密码（至少 6 位）')
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
    const user = await authStore.login(phone.value, password.value)
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
          />
          <van-field
            v-model="password"
            label="密码"
            type="password"
            maxlength="128"
            placeholder="请输入登录密码"
            autocomplete="current-password"
            :rules="[{ required: true, message: '请输入密码' }]"
          />
        </van-cell-group>

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

.login-button-wrap {
  padding: 24px 16px;
}
</style>
