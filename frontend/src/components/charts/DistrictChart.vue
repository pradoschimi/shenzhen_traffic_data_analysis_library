<script setup>
/**
 * 路段平均速度柱状图（Top 30）
 * 垂直柱状图，X 轴是路段 ID，Y 轴是速度。
 * 用来看各路段的运行效率差异。
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

  const sorted = [...props.data].sort((a, b) => b.avg_speed - a.avg_speed)

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const item = sorted[params[0].dataIndex]
        return `<b>路段: ${item.district}</b><br/>平均速度: ${item.avg_speed} km/h<br/>记录数: ${item.record_count}`
      },
    },
    toolbox: { feature: { saveAsImage: { title: '保存图片' } }, right: 10, top: -4 },
    grid: { left: 120, right: 50, top: 20, bottom: 30 },
    xAxis: { type: 'value', name: '平均速度(km/h)' },
    yAxis: {
      type: 'category',
      data: sorted.map(d => d.district),
      inverse: true,
    },
    series: [{
      type: 'bar',
      data: sorted.map(d => d.avg_speed),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(1, 0, 0, 0, [
          { offset: 0, color: '#409eff' },
          { offset: 1, color: '#79bbff' },
        ]),
      },
      label: {
        show: true,
        position: 'right',
        formatter: '{c}',
        fontSize: 11,
      },
    }],
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
