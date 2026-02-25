/**
 * 统一的 API 请求模块
 * 基于 axios 封装了一个带拦截器的客户端实例，所有接口调用都走这里。
 * 拦截器做了两件事：
 *   1. 请求时自动从 localStorage 取 JWT token 加到请求头
 *   2. 响应出错时统一弹提示（401 自动跳登录页）
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器：每次请求都带上 token，后端靠这个识别用户身份
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一处理错误，不用每个接口都写 try-catch
api.interceptors.response.use(
  response => response.data,   // 正常情况直接返回 data，省得每次取 .data
  error => {
    // 有些请求（比如图表数据）不需要弹错误提示，加 _silent 标记就行
    if (error.config?._silent) {
      return Promise.reject(error)
    }
    const status = error.response?.status
    const detail = error.response?.data?.detail || '请求失败'

    if (status === 401) {
      const url = error.config?.url || ''
      if (url.includes('/auth/login') || url.includes('/auth/register')) {
        // 登录/注册接口的 401 直接显示后端返回的错误信息
        ElMessage.error(detail)
      } else {
        // 其他接口 401 表示 token 过期，清掉本地状态踢回登录页
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        localStorage.removeItem('is_admin')
        router.push('/login')
        ElMessage.error('登录已过期，请重新登录')
      }
    } else if (status === 403) {
      ElMessage.error('没有操作权限')
    } else {
      ElMessage.error(detail)
    }
    return Promise.reject(error)
  }
)

// ==================== 登录注册相关 ====================
export const authApi = {
  login: (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),       // 获取当前登录用户信息
}

// ==================== 交通数据查询 ====================
export const trafficApi = {
  getOverview: () => api.get('/traffic/overview'),   // 首页概览卡片数据
  getRoads: (params) => api.get('/traffic/roads', { params }),
  getRecords: (params) => api.get('/traffic/records', { params }),
}

// ==================== 图表分析接口 ====================
// 这些接口都加了 _silent: true，失败时不弹错误提示
// 因为图表数据获取失败不影响整体使用，安静失败就好
export const analysisApi = {
  getHourly: (params) => api.get('/analysis/hourly', { params, _silent: true }),
  getDaily: (params) => api.get('/analysis/daily', { params, _silent: true }),
  getWorkdayWeekend: (params) => api.get('/analysis/workday-weekend', { params, _silent: true }),
  getHeatmap: (params) => api.get('/analysis/heatmap', { params, _silent: true }),
  getPeakCompare: (params) => api.get('/analysis/peak-compare', { params, _silent: true }),
  getDistrict: (params) => api.get('/analysis/district', { params, _silent: true }),
  getCongestionRank: (params) => api.get('/analysis/congestion-rank', { params, _silent: true }),
  getDistribution: (params) => api.get('/analysis/distribution', { params, _silent: true }),
  getBoxplot: (params) => api.get('/analysis/boxplot', { params, _silent: true }),
  getScatter: (params) => api.get('/analysis/scatter', { params, _silent: true }),
  getFavoriteHeatmap: () => api.get('/analysis/favorite-heatmap', { _silent: true }),
}

// ==================== 用户操作接口（收藏、建议、数据采集） ====================
export const userApi = {
  getFavorites: () => api.get('/user/favorites'),
  addFavorite: (roadsect_id) => api.post('/user/favorites', { roadsect_id }),
  removeFavorite: (roadsect_id) => api.delete(`/user/favorites/${roadsect_id}`),
  getSuggestions: (params) => api.get('/user/suggestions', { params }),
  createSuggestion: (data) => api.post('/user/suggestions', data),
  triggerFetch: (data) => api.post('/user/fetch', data),  // 管理员触发数据采集
}

export default api
