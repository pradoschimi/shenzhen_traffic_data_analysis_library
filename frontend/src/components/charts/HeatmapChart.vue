<script setup>
/**
 * 星期×小时 速度热力图
 * X 轴是 0~23 小时，Y 轴是周一到周日，颜色深浅表示速度高低。
 * 一眼就能看出哪天哪个时间段最堵。
 */
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: { type: Array, default: () => [] },
})

const chartRef = ref(null)
let chart = null

const dayLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const hourLabels = Array.from({ length: 24 }, (_, i) => `${i}:00`)

function renderChart() {
  if (!chart || !props.data.length) {
    if (chart) chart.clear()
    return
  }

  const values = props.data.map(d => [d.hour, d.day, d.avg_speed])
  const speeds = props.data.map(d => d.avg_speed)
  const minSpeed = Math.min(...speeds)
  const maxSpeed = Math.max(...speeds)

  chart.setOption({
    tooltip: {
      formatter: (params) => {
        const [hour, day, speed] = params.data
        return `${dayLabels[day]} ${hourLabels[hour]}<br/>平均速度: ${speed} km/h`
      },
    },
    toolbox: { feature: { saveAsImage: { title: '保存图片' } }, right: 0, top: -4 },
    grid: { left: 60, right: 60, top: 10, bottom: 40 },
    xAxis: { type: 'category', data: hourLabels, splitArea: { show: true } },
    yAxis: { type: 'category', data: dayLabels, splitArea: { show: true } },
    visualMap: {
      min: minSpeed,
      max: maxSpeed,
      calculable: true,
      orient: 'vertical',
      right: 0,
      top: 'center',
      inRange: {
        color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#fee090', '#fdae61', '#f46d43', '#d73027'],
      },
    },
    series: [{
      type: 'heatmap',
      data: values,
      label: { show: false },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' },
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
