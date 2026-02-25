<script setup>
/**
 * 路段速度均值-标准差散点图
 * X 轴是平均速度，Y 轴是标准差。
 * 标准差大说明该路段速度波动剧烈（不稳定），速度低+标准差大的路段是“问题路段”。
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
      formatter: (params) => {
        const item = props.data[params.dataIndex]
        const cv = item.avg_speed > 0 ? (item.std_speed / item.avg_speed * 100).toFixed(1) : 'N/A'
        return `路段: ${item.roadsect_id}<br/>
          平均速度: ${item.avg_speed} km/h<br/>
          标准差: ${item.std_speed}<br/>
          变异系数: ${cv}%`
      },
    },
    toolbox: { feature: { saveAsImage: { title: '保存图片' } }, right: 10, top: -4 },
    grid: { left: 60, right: 50, top: 20, bottom: 40 },
    xAxis: { type: 'value', name: '平均速度(km/h)', scale: true },
    yAxis: { type: 'value', name: '标准差', scale: true },
    series: [{
      type: 'scatter',
      data: props.data.map(d => [d.avg_speed, d.std_speed]),
      symbolSize: 8,
      itemStyle: {
        color: new echarts.graphic.RadialGradient(0.4, 0.3, 1, [
          { offset: 0, color: '#91bfff' },
          { offset: 1, color: '#409eff' },
        ]),
        opacity: 0.7,
      },
      emphasis: {
        itemStyle: { opacity: 1, shadowBlur: 8, shadowColor: 'rgba(64,158,255,0.4)' },
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
