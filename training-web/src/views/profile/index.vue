<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useLearningStore } from '@/stores/learning'
import { useFavoritesStore } from '@/stores/favorites'
import { showToast, showConfirmDialog } from 'vant'

const router = useRouter()
const authStore = useAuthStore()
const learningStore = useLearningStore()
const favoritesStore = useFavoritesStore()

const showLogout = ref(false)

function goRecords() {
  router.push('/profile/records')
}

function goFavoriteScripts() {
  router.push('/courses/scripts?favorites=1')
}

function goWrongBook() {
  router.push('/exam/wrong-book')
}

function editProfile() {
  showToast('编辑资料功能开发中')
}

async function handleLogout() {
  try {
    await showConfirmDialog({
      title: '退出登录',
      message: '确定要退出当前账号吗？',
      confirmButtonText: '退出',
      cancelButtonText: '取消'
    })
    authStore.logout()
    showToast('已退出登录')
    router.replace('/login')
  } catch {
    // User cancelled
  }
}

onMounted(async () => {
  try {
    const res = await import('@/api/learning').then((m) => m.learningApi.getScripts(undefined, 1, 200, true))
    const scripts = (res.data?.items || []).map((script: any) => ({
      ...script,
      summary: script.theory || '',
      isFavorite: true,
    }))
    favoritesStore.setFavorites(scripts as any)
  } catch {
    // Keep the persisted count if the network is temporarily unavailable.
  }
})
</script>

<template>
  <div class="page">
    <!-- Profile Header -->
    <div class="profile-header bg-gradient-primary">
      <div class="profile-avatar">
        <van-image
          :src="authStore.userAvatar || ''"
          round
          fit="cover"
          width="64"
          height="64"
        >
          <template v-if="!authStore.userAvatar" #error>
            <div class="avatar-placeholder">
              <van-icon name="contact" size="32" color="#fff" />
            </div>
          </template>
        </van-image>
        <div class="avatar-badge" @click="editProfile">
          <van-icon name="photograph" size="12" color="#fff" />
        </div>
      </div>
      <div class="profile-info">
        <h2 class="profile-name">{{ authStore.userName || '学员' }}</h2>
        <p class="profile-phone">{{ authStore.userPhone || '' }}</p>
        <p class="profile-store" v-if="authStore.storeName">{{ authStore.storeName }}</p>
      </div>
    </div>

    <!-- Learning Stats -->
    <div class="stats-card section-card">
      <div class="stat-row">
        <div class="stat-item" @click="goRecords">
          <span class="stat-number">{{ learningStore.totalCompletedVideos }}</span>
          <span class="stat-label">已完成课程</span>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <span class="stat-number">{{ learningStore.overallProgress }}%</span>
          <span class="stat-label">总进度</span>
        </div>
        <div class="stat-divider" />
        <div class="stat-item" @click="goFavoriteScripts">
          <span class="stat-number">{{ favoritesStore.favoriteCount }}</span>
          <span class="stat-label">收藏话术</span>
        </div>
      </div>
    </div>

    <!-- Menu List -->
    <div class="section-card">
      <van-cell-group :border="false">
        <van-cell
          title="学习记录"
          icon="notes-o"
          is-link
          @click="goRecords"
        />
        <van-cell
          title="错题本"
          icon="warning-o"
          is-link
          @click="goWrongBook"
        />
        <van-cell
          title="收藏话术"
          icon="star-o"
          is-link
          @click="goFavoriteScripts"
        />
      </van-cell-group>
    </div>

    <div class="section-card">
      <van-cell-group :border="false">
        <van-cell
          title="学习提醒"
          icon="clock-o"
          is-link
          @click="showToast('开发中')"
        />
        <van-cell
          title="关于系统"
          icon="info-o"
          is-link
          @click="showToast('眼视光销售培训系统 v1.0.0')"
        />
      </van-cell-group>
    </div>

    <!-- Logout Button -->
    <div class="logout-section">
      <van-button
        round
        block
        plain
        type="danger"
        @click="handleLogout"
      >
        退出登录
      </van-button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.profile-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px 20px 28px;
  color: #fff;
}

.profile-avatar {
  position: relative;
  flex-shrink: 0;
}

.avatar-placeholder {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-badge {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #fff;
}

.profile-info {
  flex: 1;
  min-width: 0;
}

.profile-name {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 4px;
}

.profile-phone {
  font-size: 13px;
  opacity: 0.85;
  margin-bottom: 2px;
}

.profile-store {
  font-size: 12px;
  opacity: 0.75;
}

.stats-card {
  margin-top: -12px;
  position: relative;
  z-index: 2;
}

.stat-row {
  display: flex;
  align-items: center;
  justify-content: space-around;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;

  &:active {
    opacity: 0.7;
  }
}

.stat-number {
  font-size: 22px;
  font-weight: 700;
  color: var(--primary);
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: var(--border);
}

.logout-section {
  padding: 24px 16px;
}

.van-cell {
  font-size: 14px;
}
</style>
