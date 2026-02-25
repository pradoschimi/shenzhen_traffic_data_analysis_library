/**
 * 路由配置
 * 定义了所有页面的路径和访问权限。
 * 除了登录页，其他页面都在 AppLayout 布局组件里渲染（带侧边栏和顶栏）。
 * 通过 meta 字段控制：
 *   - requiresAuth: 必须登录才能访问
 *   - requiresAdmin: 必须是管理员
 *   - guest: 已登录用户会被重定向到首页（避免重复登录）
 */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录', guest: true },
  },
  {
    path: '/',
    component: () => import('../components/AppLayout.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '数据概览' },
      },
      {
        path: 'charts',
        name: 'Charts',
        component: () => import('../views/Charts.vue'),
        meta: { title: '图表分析' },
      },
      {
        path: 'data',
        name: 'DataTable',
        component: () => import('../views/DataTable.vue'),
        meta: { title: '数据查询', requiresAuth: true },
      },
      {
        path: 'favorites',
        name: 'Favorites',
        component: () => import('../views/Favorites.vue'),
        meta: { title: '我的收藏', requiresAuth: true },
      },
      {
        path: 'suggestions',
        name: 'Suggestions',
        component: () => import('../views/Suggestions.vue'),
        meta: { title: '交通建议', requiresAuth: true },
      },
      {
        path: 'admin',
        name: 'Admin',
        component: () => import('../views/Admin.vue'),
        meta: { title: '系统管理', requiresAuth: true, requiresAdmin: true },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：每次跳转页面之前都会走这里
router.beforeEach((to, from, next) => {
  // 动态修改页面标题
  document.title = `${to.meta.title || '首页'} - 深圳交通速度分析系统`
  const token = localStorage.getItem('token')

  // 需要登录但没登录 → 跳转到登录页，并记住原来要去的页面
  if (to.meta.requiresAuth && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }

  // 需要管理员权限但不是管理员 → 踢回首页
  if (to.meta.requiresAdmin) {
    const isAdmin = localStorage.getItem('is_admin') === 'true'
    if (!isAdmin) {
      next({ name: 'Dashboard' })
      return
    }
  }

  // 已经登录了还去登录页 → 直接跳首页
  if (to.meta.guest && token) {
    next({ name: 'Dashboard' })
    return
  }

  next()
})

export default router
