<script setup>
/**
 * 首页：数据概览
 * 顶部是统计卡片（路段总数、记录数、平均速度等），
 * 下方显示 4 个核心图表的预览。
 */
import { onMounted } from 'vue'
import { useTrafficStore } from '../stores/traffic'
import OverviewCards from '../components/OverviewCards.vue'
import HourlyChart from '../components/charts/HourlyChart.vue'
import DailyChart from '../components/charts/DailyChart.vue'
import PeakCompare from '../components/charts/PeakCompare.vue'
import CongestionRank from '../components/charts/CongestionRank.vue'

const store = useTrafficStore()

onMounted(async () => {
  // 先拿概览数据（里面有 latest_date），然后拿图表数据
  // 图表数据需要知道日期范围，所以顺序不能反
  await store.fetchOverview()
  await store.fetchAllCharts()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2>数据概览:速览最新一天数据</h2>
    </div>

    <!-- 概览统计卡片：数据从 store 里拿 -->
    <OverviewCards :stats="store.overview || {}" />

    <!-- 4 个核心图表，2×2 网格布局 -->
    <el-row :gutter="16" style="margin-top: 8px;">
      <el-col :xs="24" :lg="12">
        <div class="chart-card">
          <div class="chart-title">24小时速度波动</div>
          <HourlyChart :data="store.hourlyData" />
        </div>
      </el-col>
      <el-col :xs="24" :lg="12">
        <div class="chart-card">
          <div class="chart-title">每日速度趋势</div>
          <DailyChart :data="store.dailyData" />
        </div>
      </el-col>
      <el-col :xs="24" :lg="12">
        <div class="chart-card">
          <div class="chart-title">早晚高峰对比</div>
          <PeakCompare :data="store.peakCompareData" />
        </div>
      </el-col>
      <el-col :xs="24" :lg="12">
        <div class="chart-card">
          <div class="chart-title">拥堵路段排名 (Top 20)</div>
          <CongestionRank :data="store.congestionRankData" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>
