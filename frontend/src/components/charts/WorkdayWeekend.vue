<script setup>
/**
 * 工作日 vs 周末 24小时速度对比图
 * 两条线分别表示工作日和周末的每小时平均速度，
 * 能清楚地看出工作日早晚高峰的速度明显低于周末。
 */
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: { type: Array, default: () => [] },
})

const chartRef = ref(null)
let chart = null

const colors = ['#409eff', '#e6a23c']

function renderChart() {
  if (!chart || !props.data.length) {
    if (chart) chart.clear()
    return
  }

  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`)
  const series = props.data.map((group, idx) => ({
    name: group.label,
    type: 'line',
    smooth: true,
    data: hours.map((_, h) => {
      const point = group.data.find(d => d.hour === h)
      return point ? point.avg_speed : null
    }),
    lineStyle: { width: 2.5 },
    itemStyle: { color: colors[idx % colors.length] },
  }))

  chart.setOption({
    tooltip: { trigger: 'axis' },
    toolbox: { feature: { saveAsImage: { title: '保存图片' } }, right: 10, top: -4 },
    legend: { data: props.data.map(g => g.label), bottom: 0 },
    grid: { left: 50, right: 50, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: hours, name: '时刻' },
    yAxis: { type: 'value', name: '平均速度(km/h)' },
    series,
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
