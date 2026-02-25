<script setup>
/**
 * 高峰类型速度箱线图
 * 分别显示早高峰、晚高峰、平峰三种时段的速度分布（最小值、Q1、中位数、Q3、最大值）。
 * 用 ECharts 自定义系列模拟的箱线图效果，还标注了离群点。
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

  const categories = props.data.map(d => d.label)
  // 箱线图的数据格式：[min, Q1, median, Q3, max]，对应箱体的 5 个关键值
  const boxData = props.data.map(d => [d.min_val, d.q1, d.median, d.q3, d.max_val])

  // 找出离群点（超出 Q1-1.5*IQR 或 Q3+1.5*IQR 的值）
  const outlierData = []
  props.data.forEach((d, idx) => {
    d.outliers.forEach(v => {
      outlierData.push([idx, v])
    })
  })

  chart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        if (params.seriesType === 'boxplot') {
          const item = props.data[params.dataIndex]
          return `<b>${item.label}</b><br/>
            最大: ${item.max_val}<br/>
            Q3: ${item.q3}<br/>
            中位数: ${item.median}<br/>
            Q1: ${item.q1}<br/>
            最小: ${item.min_val}`
        }
        return `离群点: ${params.data[1]} km/h`
      },
    },
    toolbox: { feature: { saveAsImage: { title: '保存图片' } }, right: 10, top: -4 },
    grid: { left: 60, right: 50, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: categories },
    yAxis: { type: 'value', name: '速度(km/h)' },
    series: [
      {
        name: '箱线图',
        type: 'boxplot',
        data: boxData,
        itemStyle: { color: '#b8d4f0', borderColor: '#409eff' },
      },
      {
        name: '离群点',
        type: 'scatter',
        data: outlierData,
        itemStyle: { color: '#f56c6c' },
        symbolSize: 5,
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
