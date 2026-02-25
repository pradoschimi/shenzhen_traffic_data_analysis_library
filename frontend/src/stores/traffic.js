/**
 * 交通数据状态管理（Pinia Store）
 * 集中管理所有图表的数据和加载状态。
 * 这样切换页面的时候不用重新请求，数据都在 store 里缓存着。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { trafficApi, analysisApi } from '../api'

export const useTrafficStore = defineStore('traffic', () => {
  // 日期范围筛选，用户在图表页选了日期后会更新这里
  const dateRange = ref([])
  const loading = ref(false)

  // 首页概览卡片的数据（总记录数、路段数等）
  const overview = ref(null)

  // 各个图表的数据，每种图表一个 ref
  const hourlyData = ref([])
  const dailyData = ref([])
  const workdayWeekendData = ref([])
  const heatmapData = ref([])
  const peakCompareData = ref([])
  const congestionRankData = ref([])
  const districtData = ref([])
  const distributionData = ref([])
  const boxplotData = ref([])
  const scatterData = ref([])
  const favoriteHeatmapData = ref([])

  // 构造请求参数：如果用户选了日期范围就用选的，没选就默认取最近 4 天
  function getParams() {
    const params = {}
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    } else if (overview.value?.latest_date) {
      const latest = new Date(overview.value.latest_date)
      const start = new Date(latest)
      start.setDate(start.getDate() - 3)
      params.start_date = start.toISOString().slice(0, 10)
      params.end_date = overview.value.latest_date
    }
    return params
  }

  async function fetchOverview() {
    overview.value = await trafficApi.getOverview()
  }

  // 一次性请求所有图表数据，用 Promise.allSettled 并发请求
  // allSettled 的好处是某个接口失败不影响其他图表的显示
  async function fetchAllCharts() {
    loading.value = true
    const params = getParams()
    try {
      const [h, d, ww, hm, pc, cr, dt, dist, bp, sc] = await Promise.allSettled([
        analysisApi.getHourly(params),
        analysisApi.getDaily(params),
        analysisApi.getWorkdayWeekend(params),
        analysisApi.getHeatmap(params),
        analysisApi.getPeakCompare(params),
        analysisApi.getCongestionRank(params),
        analysisApi.getDistrict(params),
        analysisApi.getDistribution(params),
        analysisApi.getBoxplot(params),
        analysisApi.getScatter(params),
      ])
      hourlyData.value = h.status === 'fulfilled' ? h.value : []
      dailyData.value = d.status === 'fulfilled' ? d.value : []
      workdayWeekendData.value = ww.status === 'fulfilled' ? ww.value : []
      heatmapData.value = hm.status === 'fulfilled' ? hm.value : []
      peakCompareData.value = pc.status === 'fulfilled' ? pc.value : []
      congestionRankData.value = cr.status === 'fulfilled' ? cr.value : []
      districtData.value = dt.status === 'fulfilled' ? dt.value : []
      distributionData.value = dist.status === 'fulfilled' ? dist.value : []
      boxplotData.value = bp.status === 'fulfilled' ? bp.value : []
      scatterData.value = sc.status === 'fulfilled' ? sc.value : []
    } finally {
      loading.value = false
    }
  }

  async function fetchFavoriteHeatmap() {
    favoriteHeatmapData.value = await analysisApi.getFavoriteHeatmap()
  }

  return {
    dateRange, loading, overview,
    hourlyData, dailyData, workdayWeekendData, heatmapData,
    peakCompareData, congestionRankData, districtData,
    distributionData, boxplotData, scatterData, favoriteHeatmapData,
    getParams, fetchOverview, fetchAllCharts, fetchFavoriteHeatmap,
  }
})
