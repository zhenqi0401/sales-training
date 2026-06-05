<script setup lang="ts">
withDefaults(defineProps<{
  percentage: number
  height?: number
  showLabel?: boolean
}>(), {
  height: 8,
  showLabel: true
})
</script>

<template>
  <div class="progress-bar-wrap">
    <van-progress
      :percentage="percentage"
      :stroke-width="height"
      color="linear-gradient(90deg, var(--primary), var(--success))"
      track-color="#e2e8f0"
      :show-pivot="false"
    />
    <span v-if="showLabel" class="progress-label">{{ percentage }}%</span>
  </div>
</template>

<style lang="scss" scoped>
.progress-bar-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-label {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  min-width: 36px;
  text-align: right;
}
</style>
