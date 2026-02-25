<script setup>
/**
 * 24小时速度波动折线图
 * X 轴是 0~23 小时，Y 轴是速度。
 * 展示每小时的平均/最大/最小速度，还有标准差区间（用面积图表示）。
 * 可以直观地看出早晚高峰的速度降低。
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
  const hours = props.data.map(d => `${d.hour}:00`)
  const avgSpeeds = props.data.map(d => d.avg_speed)
  const minSpeeds = props.data.map(d => d.min_speed)
  const maxSpeeds = props.data.map(d => d.max_speed)

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        const item = props.data[p.dataIndex]
        return `<b>${p.name}</b><br/>
          平均速度: ${item.avg_speed} km/h<br/>
          最高: ${item.max_speed} km/h<br/>
          最低: ${item.min_speed} km/h<br/>
          标准差: ${item.std_speed}<br/>
          记录数: ${item.record_count}`
      },
    },
    toolbox: { feature: { saveAsImage: { title: '保存图片' } }, right: 10, top: -4 },
    legend: { data: ['平均速度', '最高速度', '最低速度'], bottom: 0 },
    grid: { left: 50, right: 50, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: hours, name: '时刻' },
    yAxis: { type: 'value', name: '速度(km/h)' },
    series: [
      {
        name: '平均速度',
        type: 'line',
        data: avgSpeeds,
        smooth: true,
        lineStyle: { width: 3 },
        itemStyle: { color: '#409eff' },
        areaStyle: { color: 'rgba(64,158,255,0.1)' },
      },
      {
        name: '最高速度',
        type: 'line',
        data: maxSpeeds,
        smooth: true,
        lineStyle: { type: 'dashed', width: 1 },
        itemStyle: { color: '#67c23a' },
      },
      {
        name: '最低速度',
        type: 'line',
        data: minSpeeds,
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
