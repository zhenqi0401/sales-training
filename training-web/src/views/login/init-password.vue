<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)

function isValid() {
  if (password.value.length < 6) {
    showToast('密码至少 6 位')
    return false
  }
  if (password.value !== confirmPassword.value) {
    showToast('两次输入的密码不一致')
    return false
  }
  return true
}

async function submitPassword() {
  if (!isValid()) return
  loading.value = true
  showLoadingToast({
    message: '保存中...',
    forbidClick: true,
    duration: 0
  })
  try {
    await authStore.initPassword(password.value)
    closeToast()
    showToast('密码设置成功')
    router.replace('/home')
  } catch (e: any) {
    closeToast()
    showToast(e?.response?.data?.detail || e?.message || '保存失败，请重试')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="init-password-page">
    <div class="page-header bg-gradient-primary">
      <h1>设置登录密码</h1>
      <p>首次登录后需要设置新密码，保障账号安全</p>
    </div>

    <div class="password-form">
      <van-form @submit="submitPassword">
        <van-cell-group inset>
          <van-field
            v-model="password"
            label="新密码"
            type="password"
            placeholder="请输入新密码"
            maxlength="128"
            autocomplete="new-password"
            :rules="[{ required: true, message: '请输入新密码' }]"
          />
          <van-field
            v-model="confirmPassword"
            label="确认密码"
            type="password"
            placeholder="请再次输入新密码"
            maxlength="128"
            autocomplete="new-password"
            :rules="[{ required: true, message: '请再次输入新密码' }]"
          />
        </van-cell-group>

        <div class="submit-wrap">
          <van-button
            round
            block
            type="primary"
            native-type="submit"
            :loading="loading"
            color="linear-gradient(135deg, var(--primary), var(--primary-dark))"
            size="large"
          >
            完成设置
          </van-button>
        </div>
      </van-form>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.init-password-page {
  min-height: 100vh;
  background: $bg;
}

.page-header {
  padding: 42px 24px 32px;
  color: #fff;

  h1 {
    font-size: 24px;
    font-weight: 700;
    margin-bottom: 8px;
  }

  p {
    font-size: 14px;
    opacity: 0.86;
  }
}

.password-form {
  margin-top: -16px;
}

.submit-wrap {
  padding: 24px 16px;
}
</style>
