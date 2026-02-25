<script setup>
/**
 * 概览统计卡片组件，显示在首页顶部。
 * 展示路段总数、记录总数、全局平均速度、最高/最低速度、最新数据日期等指标。
 * 父组件通过 :stats 把数据传进来就行。
 */
import { defineProps } from 'vue'

const props = defineProps({
  stats: { type: Object, default: () => ({}) },
})

// 卡片配置：每张卡片对应 stats 里的一个字段
const cards = [
  { key: 'total_roads', label: '路段总数', icon: 'Road', color: '#409eff', suffix: '条' },
  { key: 'total_records', label: '记录总数', icon: 'Document', color: '#67c23a', suffix: '条' },
  { key: 'global_avg_speed', label: '全局平均速度', icon: 'Odometer', color: '#e6a23c', suffix: 'km/h' },
  { key: 'global_max_speed', label: '最高速度', icon: 'Top', color: '#f56c6c', suffix: 'km/h' },
  { key: 'global_min_speed', label: '最低速度', icon: 'Bottom', color: '#909399', suffix: 'km/h' },
  { key: 'latest_date', label: '最新数据日期', icon: 'Calendar', color: '#409eff', suffix: '' },
]
</script>

<template>
  <el-row :gutter="16">
    <el-col :xs="12" :sm="8" :md="4" v-for="card in cards" :key="card.key">
      <el-card class="overview-card" shadow="hover">
        <div class="stat-value" :style="{ color: card.color }">
          {{ stats[card.key] ?? '--' }}
          <span v-if="card.suffix && stats[card.key] != null" style="font-size:14px;">{{ card.suffix }}</span>
        </div>
        <div class="stat-label">
          <el-icon><component :is="card.icon" /></el-icon>
          {{ card.label }}
        </div>
      </el-card>
    </el-col>
  </el-row>
</template>

<style scoped>
.overview-card {
  margin-bottom: 16px;
  text-align: center;
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.5;
}
.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
</style>
