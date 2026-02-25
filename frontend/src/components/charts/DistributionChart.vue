<script setup>
/**
 * 速度分布直方图
 * X 轴是速度区间（比如 0-10, 10-20 km/h），Y 轴是记录数量。
 * 可以看出全市路段速度主要集中在哪个范围。
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
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const item = props.data[params[0].dataIndex]
        return `速度区间: ${item.bin_label} km/h<br/>记录数: ${item.count}`
      },
    },
    toolbox: { feature: { saveAsImage: { title: '保存图片' } }, right: 10, top: -4 },
    grid: { left: 60, right: 50, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: props.data.map(d => d.bin_label),
      name: '速度区间(km/h)',
      axisLabel: { rotate: 30 },
    },
    yAxis: { type: 'value', name: '记录数' },
    series: [{
      type: 'bar',
      data: props.data.map(d => d.count),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#409eff' },
          { offset: 1, color: '#79bbff' },
        ]),
      },
      barWidth: '60%',
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
