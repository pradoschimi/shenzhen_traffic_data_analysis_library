<script setup>
/**
 * 路段收藏热度排名图
 * 显示被用户收藏最多的路段，用水平条形图展示。
 * 明星路段一目了然。
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

  const items = [...props.data].sort((a, b) => a.fav_count - b.fav_count)

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const item = items[params[0].dataIndex]
        return `路段: ${item.roadsect_id}<br/>收藏次数: ${item.fav_count}`
      },
    },
    toolbox: { feature: { saveAsImage: { title: '保存图片' } }, right: 10, top: -4 },
    grid: { left: 120, right: 40, top: 10, bottom: 20 },
    xAxis: { type: 'value', name: '收藏次数' },
    yAxis: {
      type: 'category',
      data: items.map(d => String(d.roadsect_id)),
      inverse: false,
      axisLabel: { fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: items.map(d => ({
        value: d.fav_count,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(1, 0, 0, 0, [
            { offset: 0, color: '#f56c6c' },
            { offset: 1, color: '#fca5a5' },
          ]),
        },
      })),
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
