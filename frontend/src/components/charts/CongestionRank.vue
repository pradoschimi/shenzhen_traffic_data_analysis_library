<script setup>
/**
 * 拥堵路段排名图（Top N）
 * 水平条形图，按平均速度从低到高排列。
 * 速度最低的路段即为最拥堵的路段。
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

  // 后端返回的列表已经按速度从低到高排好了，最堵的在前面
  const items = [...props.data].slice(0, 20)

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const item = items[params[0].dataIndex]
        return `<b>${item.road_name || item.roadsect_id}</b><br/>
          平均速度: ${item.avg_speed} km/h<br/>
          记录数: ${item.record_count}`
      },
    },
    toolbox: { feature: { saveAsImage: { title: '保存图片' } }, right: 0, top: -4 },
    grid: { left: 140, right: 40, top: 10, bottom: 20 },
    xAxis: { type: 'value', name: '平均速度(km/h)' },
    yAxis: {
      type: 'category',
      data: items.map(d => d.road_name || d.roadsect_id).map(
        name => name.length > 12 ? name.slice(0, 12) + '...' : name
      ),
      inverse: true,
      axisLabel: { fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: items.map(d => ({
        value: d.avg_speed,
        itemStyle: {
          color: d.avg_speed < 20 ? '#f56c6c' : d.avg_speed < 40 ? '#e6a23c' : '#409eff',
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
