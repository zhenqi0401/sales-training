<script setup lang="ts">
defineProps<{
  role: 'student' | 'teacher'
  name: string
  content: string
  time?: string
  avatar?: string
}>()
</script>

<template>
  <div class="dialogue-box" :class="role">
    <div class="dialogue-avatar" v-if="avatar">
      <van-image :src="avatar" round fit="cover" width="32" height="32" />
    </div>
    <div class="dialogue-content">
      <div class="dialogue-name">{{ name }}</div>
      <div class="dialogue-bubble">{{ content }}</div>
      <div class="dialogue-time" v-if="time">{{ time }}</div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.dialogue-box {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  padding: 0 16px;

  &.student {
    flex-direction: row-reverse;

    .dialogue-avatar {
      margin-left: 0;
    }

    .dialogue-bubble {
      background: linear-gradient(135deg, var(--primary), var(--primary-dark));
      color: #fff;
      border-bottom-right-radius: 4px;
    }

    .dialogue-name {
      text-align: right;
      color: var(--primary);
    }

    .dialogue-time {
      text-align: right;
    }
  }

  &.teacher {
    .dialogue-bubble {
      background: #f0f0f0;
      color: var(--text);
      border-bottom-left-radius: 4px;
    }

    .dialogue-name {
      color: var(--text-secondary);
    }
  }
}

.dialogue-content {
  max-width: 75%;
}

.dialogue-name {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 4px;
}

.dialogue-bubble {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.dialogue-time {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 4px;
}
</style>
