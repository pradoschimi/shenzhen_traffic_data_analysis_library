<script setup>
/**
 * 早晚高峰对比柱状图
 * 拿早高峰（7-9点）、晚高峰（17-19点）、平峰三种时段的平均速度对比。
 * 柱子上方还显示了标准差，可以看出速度的波动程度。
 */
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: { type: Array, default: () => [] },
})

const chartRef = ref(null)
let chart = null

const peakColors = {
  '早高峰': '#e6a23c',
  '晚高峰': '#f56c6c',
  '平峰': '#409eff',
}

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
        return `<b>${item.peak_type}</b><br/>
          平均速度: ${item.avg_speed} km/h<br/>
          标准差: ${item.std_speed}<br/>
          记录数: ${item.record_count}`
      },
    },
    toolbox: { feature: { saveAsImage: { title: '保存图片' } }, right: 10, top: -4 },
    grid: { left: 60, right: 50, top: 20, bottom: 30 },
    xAxis: {
      type: 'category',
      data: props.data.map(d => d.peak_type),
    },
    yAxis: { type: 'value', name: '平均速度(km/h)' },
    series: [{
      type: 'bar',
      data: props.data.map(d => ({
        value: d.avg_speed,
        itemStyle: { color: peakColors[d.peak_type] || '#909399' },
      })),
      barWidth: '40%',
      label: {
        show: true,
        position: 'top',
        formatter: '{c} km/h',
        fontSize: 12,
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
