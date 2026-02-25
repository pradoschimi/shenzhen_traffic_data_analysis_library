<script setup>
/**
 * 图表分析页，集中展示全部 10 种图表。
 * 支持日期范围筛选和一键导出 CSV。
 */
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useTrafficStore } from '../stores/traffic'
import HourlyChart from '../components/charts/HourlyChart.vue'
import DailyChart from '../components/charts/DailyChart.vue'
import WorkdayWeekend from '../components/charts/WorkdayWeekend.vue'
import HeatmapChart from '../components/charts/HeatmapChart.vue'
import PeakCompare from '../components/charts/PeakCompare.vue'
import CongestionRank from '../components/charts/CongestionRank.vue'
import DistrictChart from '../components/charts/DistrictChart.vue'
import DistributionChart from '../components/charts/DistributionChart.vue'
import BoxplotChart from '../components/charts/BoxplotChart.vue'
import ScatterChart from '../components/charts/ScatterChart.vue'

const store = useTrafficStore()

// 如果从别的页面切过来，而且 store 里已经有数据了，就不重新请求
onMounted(() => {
  if (store.hourlyData.length === 0) {
    store.fetchAllCharts()
  }
})

// 用户改了日期范围，重新拉所有图表数据
function handleDateChange() {
  store.fetchAllCharts()
}

/**
 * 导出 CSV 文件，把所有图表的数据打包成一个文件下载。
 * 加了 BOM 头（\uFEFF）让 Excel 识别 UTF-8 编码，不然中文会乱码。
 */
function exportCSV() {
  const datasets = [
    { name: '24小时速度波动', data: store.hourlyData, cols: ['hour','avg_speed','min_speed','max_speed','std_speed','record_count'] },
    { name: '每日速度趋势', data: store.dailyData, cols: ['date','avg_speed','min_speed','max_speed','record_count'] },
    { name: '工作日周末对比', data: store.workdayWeekendData, flatten: g => g.data?.map(d => ({ label: g.label, ...d })) || [], cols: ['label','hour','avg_speed'] },
    { name: '高峰对比', data: store.peakCompareData, cols: ['peak_type','avg_speed','std_speed','record_count'] },
    { name: '拥堵排名', data: store.congestionRankData, cols: ['roadsect_id','road_name','avg_speed','record_count'] },
    { name: '速度分布', data: store.distributionData, cols: ['bin_label','count'] },
    { name: '箱线图', data: store.boxplotData, cols: ['label','min_val','q1','median','q3','max_val'] },
    { name: '散点图', data: store.scatterData, cols: ['roadsect_id','avg_speed','std_speed'] },
  ]

  let csv = '\uFEFF' // BOM for Excel
  for (const ds of datasets) {
    csv += `\n=== ${ds.name} ===\n`
    let rows = ds.data || []
    if (ds.flatten && rows.length) rows = rows.flatMap(ds.flatten)
    const cols = ds.cols
    csv += cols.join(',') + '\n'
    for (const row of rows) {
      csv += cols.map(c => row[c] ?? '').join(',') + '\n'
    }
  }

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `交通分析数据_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('CSV 导出成功')
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2>图表分析</h2>
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-date-picker
          v-model="store.dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="起始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          @change="handleDateChange"
          style="width: 280px;"
        />
        <el-button type="success" @click="exportCSV" :icon="'Download'">导出 CSV</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <!-- 图表1: 24小时速度波动 -->
      <el-col :xs="24" :lg="12">
        <div class="chart-card">
          <div class="chart-title">图表1: 24小时速度波动折线图</div>
          <HourlyChart :data="store.hourlyData" />
        </div>
      </el-col>

      <!-- 图表2: 工作日/周末对比 -->
      <el-col :xs="24" :lg="12">
        <div class="chart-card">
          <div class="chart-title">图表2: 工作日/周末速度对比</div>
          <WorkdayWeekend :data="store.workdayWeekendData" />
        </div>
      </el-col>

      <!-- 图表3: 热力图 -->
      <el-col :xs="24" :lg="12">
        <div class="chart-card">
          <div class="chart-title">图表3: 星期-小时速度热力图</div>
          <HeatmapChart :data="store.heatmapData" />
        </div>
      </el-col>

      <!-- 图表4: 早晚高峰对比 -->
      <el-col :xs="24" :lg="12">
        <div class="chart-card">
          <div class="chart-title">图表4: 早晚高峰速度对比</div>
          <PeakCompare :data="store.peakCompareData" />
        </div>
      </el-col>

      <!-- 图表5: 拥堵排名 -->
      <el-col :xs="24" :lg="12">
        <div class="chart-card">
          <div class="chart-title">图表5: 拥堵路段排名 (Top 20)</div>
          <CongestionRank :data="store.congestionRankData" />
        </div>
      </el-col>

      <!-- 图表6: 路段平均速度 -->
      <el-col :xs="24" :lg="12">
        <div class="chart-card">
          <div class="chart-title">图表6: 路段平均速度柱状图 (Top 30)</div>
          <DistrictChart :data="store.districtData" />
        </div>
      </el-col>

      <!-- 图表7: 速度分布 -->
      <el-col :xs="24" :lg="12">
        <div class="chart-card">
          <div class="chart-title">图表7: 速度分布直方图</div>
          <DistributionChart :data="store.distributionData" />
        </div>
      </el-col>

      <!-- 图表8: 箱线图 -->
      <el-col :xs="24" :lg="12">
        <div class="chart-card">
          <div class="chart-title">图表8: 高峰类型速度箱线图</div>
          <BoxplotChart :data="store.boxplotData" />
        </div>
      </el-col>

      <!-- 图表9: 散点图 -->
      <el-col :xs="24" :lg="12">
        <div class="chart-card">
          <div class="chart-title">图表9: 路段速度均值-标准差散点图</div>
          <ScatterChart :data="store.scatterData" />
        </div>
      </el-col>

      <!-- 图表10: 每日速度趋势 -->
      <el-col :xs="24" :lg="12">
        <div class="chart-card">
          <div class="chart-title">图表10: 每日速度趋势折线图</div>
          <DailyChart :data="store.dailyData" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>
