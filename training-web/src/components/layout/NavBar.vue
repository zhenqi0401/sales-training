<script setup lang="ts">
import { useRouter } from 'vue-router'

const props = withDefaults(defineProps<{
  title: string
  leftArrow?: boolean
  rightText?: string
}>(), {
  leftArrow: true,
  rightText: ''
})

const emit = defineEmits<{
  clickRight: []
  clickLeft: []
}>()

const router = useRouter()

function onClickLeft() {
  emit('clickLeft')
  if (props.leftArrow) {
    router.back()
  }
}
</script>

<template>
  <van-nav-bar
    :title="title"
    :left-arrow="leftArrow"
    :right-text="rightText"
    fixed
    placeholder
    border
    safe-area-inset-top
    @click-left="onClickLeft"
    @click-right="emit('clickRight')"
  >
    <template #right>
      <slot name="right" />
    </template>
    <template #title>
      <slot name="title">
        <span class="nav-title">{{ title }}</span>
      </slot>
    </template>
  </van-nav-bar>
</template>

<style lang="scss" scoped>
.nav-title {
  font-size: 17px;
  font-weight: 600;
  color: $text;
}
</style>
