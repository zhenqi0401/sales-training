<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import type { Product, ProductSpec, ProductFAQ } from '@/types'

const route = useRoute()
const router = useRouter()
const productId = computed(() => Number(route.params.id))

const product = ref<Product | null>(null)
const loading = ref(true)
const activeTab = ref(0)

// Mock product data
const mockProducts: Record<number, Product> = {
  1: {
    id: 1, categoryId: 1, name: 'TR90超轻镜架', brand: '品牌A',
    image: '', description: '采用TR90记忆材料，超轻设计，佩戴舒适不易变形。',
    sellingPoints: ['超轻材质仅8g', '记忆不变形', '亲肤防过敏', '多色可选'],
    specs: [
      { label: '材质', value: 'TR90' },
      { label: '重量', value: '8g' },
      { label: '尺寸', value: '53-17-140' },
      { label: '颜色', value: '黑色/玳瑁/透明' }
    ],
    faq: [
      { question: 'TR90材料有什么特点？', answer: 'TR90是瑞士EMS公司研发的记忆性高分子材料，具有超轻、超韧、耐高温等特点，是目前最优秀的眼镜框材料之一。' },
      { question: '如何保养镜架？', answer: '建议用中性清洁剂清洗，避免接触化学溶剂，不佩戴时放入镜盒。' }
    ]
  },
  2: {
    id: 2, categoryId: 1, name: '钛合金商务镜架', brand: '品牌B',
    image: '', description: '纯钛材质，商务经典设计，轻便耐腐蚀。',
    sellingPoints: ['纯钛材质', '商务设计', '抗腐蚀', '超轻佩戴'],
    specs: [
      { label: '材质', value: '纯钛' },
      { label: '重量', value: '10g' },
      { label: '尺寸', value: '54-18-140' },
      { label: '颜色', value: '银色/枪色' }
    ],
    faq: [
      { question: '钛合金镜架有什么优势？', answer: '钛合金具有重量轻、强度高、耐腐蚀、不过敏等优点，特别适合商务人士和敏感肌肤人群。' }
    ]
  },
  3: {
    id: 3, categoryId: 2, name: '防蓝光镜片', brand: '品牌C',
    image: '', description: '有效过滤有害蓝光，保护眼睛健康。',
    sellingPoints: ['过滤有害蓝光', '清晰透亮', 'UV防护', '抗疲劳'],
    specs: [
      { label: '折射率', value: '1.60' },
      { label: '透光率', value: '>98%' },
      { label: '功能', value: '防蓝光/抗UV' },
      { label: '材质', value: '树脂' }
    ],
    faq: [
      { question: '防蓝光镜片对眼睛有什么好处？', answer: '能有效过滤电子产品发出的有害蓝光，减轻眼睛疲劳，保护视网膜，改善睡眠质量。' }
    ]
  }
}

onMounted(async () => {
  try {
    product.value = mockProducts[productId.value] || Object.values(mockProducts)[0]
  } catch {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page-no-tabbar">
    <van-nav-bar
      title="产品详情"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    />

    <van-loading v-if="loading" size="24" class="page-loading" />

    <template v-else-if="product">
      <!-- Product Image -->
      <div class="product-image">
        <van-image
          :src="product.image || 'https://fastly.jsdelivr.net/npm/@vant/assets/apple-1.jpeg'"
          fit="contain"
          width="100%"
          height="200"
        />
      </div>

      <!-- Basic Info -->
      <div class="product-info section-card">
        <h2 class="product-name">{{ product.name }}</h2>
        <span class="product-brand">{{ product.brand }}</span>
        <p class="product-desc">{{ product.description }}</p>

        <!-- Selling Points -->
        <div class="selling-points">
          <van-tag
            v-for="(point, idx) in product.sellingPoints"
            :key="idx"
            round
            color="var(--success-light)"
            text-color="var(--success)"
            style="margin-right: 6px; margin-bottom: 6px;"
          >
            {{ point }}
          </van-tag>
        </div>
      </div>

      <!-- Tabs: Specs & FAQ -->
      <div class="section-card">
        <van-tabs v-model:active="activeTab" color="var(--primary)" title-active-color="var(--primary)">
          <van-tab title="规格参数">
            <div class="spec-list">
              <div v-for="(spec, idx) in product.specs" :key="idx" class="spec-item">
                <span class="spec-label">{{ spec.label }}</span>
                <span class="spec-value">{{ spec.value }}</span>
              </div>
            </div>
          </van-tab>
          <van-tab title="常见问题">
            <div v-if="product.faq.length === 0" class="faq-empty">
              <span class="text-muted">暂无常见问题</span>
            </div>
            <div v-for="(faq, idx) in product.faq" :key="idx" class="faq-item">
              <div class="faq-q">
                <van-icon name="question-o" color="var(--primary)" />
                {{ faq.question }}
              </div>
              <div class="faq-a">
                <van-icon name="chat-o" color="var(--success)" />
                {{ faq.answer }}
              </div>
            </div>
          </van-tab>
        </van-tabs>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.page-loading {
  padding: 60px 0;
}

.product-image {
  background: $card;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.product-info {
  margin-top: 0;
  margin-bottom: 12px;
}

.product-name {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 6px;
}

.product-brand {
  display: inline-block;
  font-size: 12px;
  color: var(--primary);
  background: rgba(14, 116, 144, 0.1);
  padding: 2px 10px;
  border-radius: 10px;
  margin-bottom: 10px;
}

.product-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 12px;
}

.selling-points {
  display: flex;
  flex-wrap: wrap;
}

.spec-list {
  padding: 12px 0;
}

.spec-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-light);

  &:last-child {
    border-bottom: none;
  }
}

.spec-label {
  font-size: 14px;
  color: var(--text-muted);
}

.spec-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.faq-empty {
  padding: 24px;
  text-align: center;
}

.faq-item {
  padding: 14px 0;
  border-bottom: 1px solid var(--border-light);

  &:last-child {
    border-bottom: none;
  }
}

.faq-q {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 8px;
}

.faq-a {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
  padding-left: 22px;
}
</style>
