<template>
  <div class="page-container">
    <div class="page-header">
      <h2>用户详情</h2>
      <p>查看用户的学习进度和考试记录</p>
    </div>

    <!-- User Info Card -->
    <el-card shadow="hover" class="mb-4">
      <template #header>
        <div class="card-header">
          <span>基本信息</span>
          <el-button size="small" @click="$router.push('/users')">返回列表</el-button>
        </div>
      </template>
      <el-row :gutter="24">
        <el-col :span="4" class="avatar-col">
          <el-avatar :size="80" :src="userInfo.avatar" :icon="'UserFilled'" />
        </el-col>
        <el-col :span="20">
          <el-descriptions :column="4" border size="small">
            <el-descriptions-item label="用户名">{{ userInfo.username }}</el-descriptions-item>
            <el-descriptions-item label="姓名">{{ userInfo.realName }}</el-descriptions-item>
            <el-descriptions-item label="角色">
              <el-tag v-if="userInfo.role === 'admin'" type="danger" size="small">管理员</el-tag>
              <el-tag v-else-if="userInfo.role === 'trainer'" type="warning" size="small">培训师</el-tag>
              <el-tag v-else type="primary" size="small">学员</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="userInfo.status === 1 ? 'success' : 'danger'" size="small">
                {{ userInfo.status === 1 ? '启用' : '禁用' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="手机号">{{ userInfo.phone || '--' }}</el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ userInfo.email || '--' }}</el-descriptions-item>
            <el-descriptions-item label="所属门店">{{ userInfo.storeName || '--' }}</el-descriptions-item>
            <el-descriptions-item label="注册时间">{{ userInfo.createdAt }}</el-descriptions-item>
          </el-descriptions>
        </el-col>
      </el-row>
    </el-card>

    <!-- Progress -->
    <el-card shadow="hover" class="mb-4">
      <template #header>
        <span>学习进度</span>
      </template>
      <el-table :data="progressList" stripe size="small">
        <el-table-column prop="videoTitle" label="视频名称" min-width="200" />
        <el-table-column label="完成度" width="200">
          <template #default="{ row }">
            <el-progress :percentage="row.progress || 0" :status="row.progress >= 100 ? 'success' : undefined" />
          </template>
        </el-table-column>
        <el-table-column prop="lastWatchAt" label="上次观看" width="180" />
      </el-table>
      <el-empty v-if="progressList.length === 0" description="暂无学习记录" />
    </el-card>

    <!-- Exam Records -->
    <el-card shadow="hover">
      <template #header>
        <span>考试记录</span>
      </template>
      <el-table :data="examRecords" stripe size="small">
        <el-table-column prop="examTitle" label="试卷名称" min-width="200" />
        <el-table-column prop="score" label="得分" width="80" align="center">
          <template #default="{ row }">
            <span :class="row.score >= 60 ? 'score-pass' : 'score-fail'">{{ row.score }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="totalScore" label="总分" width="80" align="center" />
        <el-table-column label="结果" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.passed ? 'success' : 'danger'" size="small">
              {{ row.passed ? '通过' : '未通过' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="用时(分钟)" width="100" align="center" />
        <el-table-column prop="submitTime" label="提交时间" width="180" />
      </el-table>
      <el-empty v-if="examRecords.length === 0" description="暂无考试记录" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getUserDetail } from '@/api/users'
import type { UserInfo } from '@/types'

const route = useRoute()
const userInfo = ref<UserInfo>({
  id: 0,
  username: '',
  realName: '',
  role: 'student',
  status: 1,
  createdAt: '',
})
const progressList = ref<any[]>([])
const examRecords = ref<any[]>([])

onMounted(async () => {
  const id = Number(route.params.id)
  if (!id) return

  try {
    const data = await getUserDetail(id)
    userInfo.value = data
    progressList.value = data.videoProgress || []
    examRecords.value = data.examRecords || []
  } catch {
    // Demo data
    userInfo.value = { id, username: 'demo_user', realName: '张三', role: 'student', status: 1, createdAt: '2026-01-15 10:30:00', storeName: '旗舰店' }
    progressList.value = [
      { videoTitle: '渐进多焦点镜片销售技巧', progress: 100, lastWatchAt: '2026-05-20 14:30' },
      { videoTitle: '防蓝光镜片知识讲解', progress: 60, lastWatchAt: '2026-05-18 10:00' },
      { videoTitle: '客户接待流程规范', progress: 30, lastWatchAt: '2026-05-15 16:20' },
    ]
    examRecords.value = [
      { examTitle: '初级销售资格认证', score: 85, totalScore: 100, passed: true, duration: 45, submitTime: '2026-05-22 11:00' },
      { examTitle: '产品知识水平测试', score: 58, totalScore: 100, passed: false, duration: 38, submitTime: '2026-05-10 09:30' },
    ]
  }
})
</script>

<style scoped lang="scss">
.mb-4 { margin-bottom: 16px; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.avatar-col {
  display: flex;
  align-items: center;
  justify-content: center;
}

.score-pass { color: #67c23a; font-weight: 600; }
.score-fail { color: #f56c6c; font-weight: 600; }
</style>
