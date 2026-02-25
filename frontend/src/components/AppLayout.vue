<script setup>
/**
 * 主布局组件：左侧导航栏 + 顶栏 + 右侧内容区
 * 除了登录页之外的所有页面都套在这个布局里。
 * 导航树会根据登录状态和管理员权限动态显示菜单项。
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const isCollapse = ref(false)  // 侧边栏是否收起

// 动态生成菜单列表：未登录只能看概览和图表，登录后能看更多功能
const menuItems = computed(() => {
  const items = [
    { index: '/', icon: 'DataAnalysis', title: '数据概览' },
    { index: '/charts', icon: 'PieChart', title: '图表分析' },
  ]
  if (authStore.isLoggedIn) {
    items.push(
      { index: '/data', icon: 'Grid', title: '数据查询' },
      { index: '/favorites', icon: 'Star', title: '我的收藏' },
      { index: '/suggestions', icon: 'ChatLineRound', title: '交通建议' },
    )
    if (authStore.isAdmin) {
      items.push({ index: '/admin', icon: 'Setting', title: '系统管理' })
    }
  }
  return items
})

function handleSelect(index) {
  router.push(index)
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="layout-container">
    <!-- 左侧导航栏：深色背景，点击 logo 区域可以展开/收起 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="layout-aside">
      <div class="aside-header" @click="isCollapse = !isCollapse">
        <img src="/traffic.png" alt="logo" style="width: 32px; height: 32px; border-radius: 4px;" />
        <span v-show="!isCollapse" class="aside-title">深圳交通分析</span>
      </div>
      <el-menu
        :default-active="$route.path"
        :collapse="isCollapse"
        background-color="#001529"
        text-color="#ffffffb3"
        active-text-color="#409eff"
        @select="handleSelect"
        :collapse-transition="false"
      >
        <el-menu-item v-for="item in menuItems" :key="item.index" :index="item.index">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 右侧：顶栏 + 内容区 -->
    <el-container>
      <!-- 顶栏：左侧面包屑导航，右侧用户信息和登出按钮 -->
      <el-header class="layout-header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="$route.meta.title">
              {{ $route.meta.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <template v-if="authStore.isLoggedIn">
            <span class="user-info">
              <el-icon><User /></el-icon>
              {{ authStore.nickname || authStore.username }}
              <el-tag v-if="authStore.isAdmin" size="small" type="danger" style="margin-left: 4px;">管理员</el-tag>
            </span>
            <el-button text @click="handleLogout">退出登录</el-button>
          </template>
          <template v-else>
            <el-button type="primary" @click="$router.push('/login')">登录</el-button>
          </template>
        </div>
      </el-header>

      <!-- 主内容区：路由切换时有个淡入淡出的过渡动画 -->
      <el-main class="layout-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout-container {
  height: 100vh;
}
.layout-aside {
  background: #001529;
  transition: width 0.2s;
  overflow: hidden;
}
.aside-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  border-bottom: 1px solid #ffffff1a;
}
.aside-title {
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
}
.layout-header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  padding: 0 20px;
  height: 56px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: #606266;
}
.layout-main {
  background: #f0f2f5;
  overflow-y: auto;
}
.el-menu {
  border-right: none;
}
</style>
