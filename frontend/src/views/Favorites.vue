<script setup>
/**
 * 我的收藏页：查看和管理收藏的路段，还能看到收藏热度排名图表。
 */
import { ref, onMounted } from 'vue'
import { userApi } from '../api'
import { useTrafficStore } from '../stores/traffic'
import { ElMessage, ElMessageBox } from 'element-plus'
import FavoriteHeatmap from '../components/charts/FavoriteHeatmap.vue'

const store = useTrafficStore()
const loading = ref(false)
const favorites = ref([])
const newRoadsectId = ref('')

async function fetchFavorites() {
  loading.value = true
  try {
    favorites.value = await userApi.getFavorites()
  } finally {
    loading.value = false
  }
}

async function addFavorite() {
  if (!newRoadsectId.value.trim()) {
    ElMessage.warning('请输入路段ID')
    return
  }
  try {
    await userApi.addFavorite(newRoadsectId.value.trim())
    ElMessage.success('收藏成功')
    newRoadsectId.value = ''
    fetchFavorites()
  } catch (err) {
    // 已由拦截器处理
  }
}

async function removeFavorite(roadsectId) {
  try {
    await ElMessageBox.confirm(`确定取消收藏路段 ${roadsectId} 吗？`, '确认')
    await userApi.removeFavorite(roadsectId)
    ElMessage.success('已取消收藏')
    fetchFavorites()
  } catch (err) {
    // 用户可能点了取消，或者请求失败（拦截器已处理）
  }
}

onMounted(() => {
  fetchFavorites()
  store.fetchFavoriteHeatmap()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2>我的收藏</h2>
      <div style="display: flex; gap: 8px;">
        <el-input
          v-model="newRoadsectId"
          placeholder="输入路段ID添加收藏"
          style="width: 200px;"
          @keyup.enter="addFavorite"
        />
        <el-button type="primary" @click="addFavorite" :icon="'Star'">添加收藏</el-button>
      </div>
    </div>

    <el-card shadow="never">
      <el-table :data="favorites" v-loading="loading" stripe border>
        <el-table-column type="index" label="#" width="60" />
        <el-table-column prop="roadsect_id" label="路段ID" />
        <el-table-column prop="created_at" label="收藏时间" width="200">
          <template #default="{ row }">
            {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="danger" text size="small" @click="removeFavorite(row.roadsect_id)">
              取消收藏
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && favorites.length === 0" description="暂无收藏路段" />
    </el-card>

    <!-- 收藏热度图表，有数据时才显示 -->
    <el-card shadow="never" style="margin-top: 16px;" v-if="store.favoriteHeatmapData.length > 0">
      <template #header>
        <span style="font-weight: 600;">路段收藏热度排名</span>
      </template>
      <FavoriteHeatmap :data="store.favoriteHeatmapData" />
    </el-card>
  </div>
</template>
