<script setup>
/**
 * 每日速度趋势折线图
 * X 轴是日期，Y 轴是速度，一条线连接每天的平均速度。
 * 可以看出速度随日期的变化趋势（比如周末通常比工作日快）。
 */
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: { type: Array, default: () => [] },
})

const chartRef = ref(null)
let chart = null

function renderChart() {
  if (!chart || !props.data.length) {
    if (chart) chart.clear()
    return
  }
  chart.setOption({
    tooltip: { trigger: 'axis' },
    toolbox: { feature: { saveAsImage: { title: '保存图片' } }, right: 10, top: -4 },
    legend: { data: ['平均速度', '最高速度', '最低速度'], bottom: 0 },
    grid: { left: 50, right: 50, top: 20, bottom: 40 },
    dataZoom: [{ type: 'inside', start: 0, end: 100 }],
    xAxis: {
      type: 'category',
      data: props.data.map(d => d.date),
      axisLabel: { rotate: 30 },
    },
    yAxis: { type: 'value', name: '速度(km/h)' },
    series: [
      {
        name: '平均速度',
        type: 'line',
        data: props.data.map(d => d.avg_speed),
        smooth: true,
        lineStyle: { width: 2 },
        itemStyle: { color: '#409eff' },
        areaStyle: { color: 'rgba(64,158,255,0.08)' },
      },
      {
        name: '最高速度',
        type: 'line',
        data: props.data.map(d => d.max_speed),
        smooth: true,
        lineStyle: { type: 'dashed', width: 1 },
        itemStyle: { color: '#67c23a' },
      },
      {
        name: '最低速度',
        type: 'line',
        data: props.data.map(d => d.min_speed),
        smooth: true,
        lineStyle: { type: 'dashed', width: 1 },
        itemStyle: { color: '#f56c6c' },
      },
    ],
  })
}

watch(() => props.data, renderChart, { deep: true })

onMounted(() => {
  chart = echarts.init(chartRef.value)
  renderChart()
  window.addEventListener('resize', () => chart?.resize())
})

onBeforeUnmount(() => {
  chart?.dispose()
})
</script>

<template>
  <div ref="chartRef" class="chart-container"></div>
</template>
