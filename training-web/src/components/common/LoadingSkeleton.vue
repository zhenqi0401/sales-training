<script setup lang="ts">
withDefaults(defineProps<{
  row?: number
  type?: 'card' | 'text' | 'circle'
}>(), {
  row: 3,
  type: 'card'
})
</script>

<template>
  <div class="loading-skeleton">
    <template v-if="type === 'card'">
      <div v-for="i in row" :key="i" class="skeleton-card">
        <div class="skeleton skeleton-thumb" />
        <div class="skeleton-info">
          <div class="skeleton skeleton-title" />
          <div class="skeleton skeleton-desc" />
        </div>
      </div>
    </template>
    <template v-else-if="type === 'circle'">
      <div class="skeleton-row" v-for="i in row" :key="i">
        <div class="skeleton skeleton-circle" />
        <div class="skeleton skeleton-line" />
      </div>
    </template>
    <template v-else>
      <div v-for="i in row" :key="i" class="skeleton skeleton-text" />
    </template>
  </div>
</template>

<style lang="scss" scoped>
.loading-skeleton {
  padding: 16px;
}

.skeleton-card {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.skeleton-thumb {
  width: 120px;
  height: 72px;
  border-radius: 8px;
  flex-shrink: 0;
}

.skeleton-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-title {
  height: 16px;
  width: 70%;
}

.skeleton-desc {
  height: 12px;
  width: 50%;
}

.skeleton-text {
  height: 14px;
  margin-bottom: 12px;
  width: 100%;
}

.skeleton-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.skeleton-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  flex-shrink: 0;
}

.skeleton-line {
  height: 14px;
  flex: 1;
}
</style>
