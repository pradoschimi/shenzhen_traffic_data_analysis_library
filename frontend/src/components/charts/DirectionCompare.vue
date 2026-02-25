<script setup>
/**
 * 路段早晚高峰速度差异对比图
 * 显示同一路段早高峰和晚高峰的速度差值。
 * 差值大的路段可能存在方向性拥堵（早上进城堵、晚上出城堵，或者反过来）。
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

  // 按早晚高峰速度差的绝对值排序，差异最大的路段排在最上面
  const sorted = [...props.data].sort((a, b) => Math.abs(a.diff) - Math.abs(b.diff))
  const labels = sorted.map(d => String(d.roadsect_id))

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const idx = params[0].dataIndex
        const item = sorted[idx]
        return `<b>路段 ${item.roadsect_id}</b><br/>
          早高峰: ${item.am_speed} km/h<br/>
          晚高峰: ${item.pm_speed} km/h<br/>
          差值: ${item.diff > 0 ? '+' : ''}${item.diff} km/h`
      },
    },
    toolbox: { feature: { saveAsImage: { title: '保存图片' } }, right: 10, top: -4 },
    legend: { data: ['早高峰', '晚高峰'], bottom: 0 },
    grid: { left: 120, right: 40, top: 10, bottom: 40 },
    xAxis: { type: 'value', name: '速度(km/h)' },
    yAxis: {
      type: 'category',
      data: labels,
      axisLabel: { fontSize: 10 },
    },
    series: [
      {
        name: '早高峰',
        type: 'bar',
        data: sorted.map(d => d.am_speed),
        itemStyle: { color: '#e6a23c' },
        barGap: '10%',
      },
      {
        name: '晚高峰',
        type: 'bar',
        data: sorted.map(d => d.pm_speed),
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
