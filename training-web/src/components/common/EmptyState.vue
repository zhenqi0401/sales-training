<script setup lang="ts">
withDefaults(defineProps<{
  description?: string
  image?: string
}>(), {
  description: '暂无数据',
  image: ''
})
</script>

<template>
  <div class="empty-state">
    <van-empty :image="image || 'default'" :description="description">
      <template #image>
        <div class="empty-icon">
          <van-icon name="info-o" size="64" color="var(--text-muted)" />
        </div>
      </template>
    </van-empty>
  </div>
</template>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px 0;
}

.empty-icon {
  display: flex;
  justify-content: center;
  margin-bottom: 8px;
}
</style>
