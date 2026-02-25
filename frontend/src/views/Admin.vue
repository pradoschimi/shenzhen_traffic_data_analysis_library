<script setup>
/**
 * 系统管理页（管理员专用）
 * 可以触发数据采集任务，查看路段信息。
 * 数据集是静态的（约 1017 万条），通过分页方式采集入库。
 */
import { ref, reactive } from 'vue'
import { userApi, trafficApi } from '../api'
import { ElMessage } from 'element-plus'

const fetchLoading = ref(false)
const fetchForm = reactive({
  start_page: 1,
  max_pages: 100,
  rows_per_page: 1000,
})
const fetchResult = ref(null)

// 路段信息列表（下半部分显示）
const roadsLoading = ref(false)
const roads = ref([])
const roadsTotal = ref(0)
const roadsPage = ref(1)

async function triggerFetch() {
  fetchLoading.value = true
  try {
    const res = await userApi.triggerFetch(fetchForm)
    fetchResult.value = res
    ElMessage.success(res.message || '采集任务已提交')
  } catch (err) {
    // 已由拦截器处理
  } finally {
    fetchLoading.value = false
  }
}

async function fetchRoads() {
  roadsLoading.value = true
  try {
    const res = await trafficApi.getRoads({ page: roadsPage.value, page_size: 50 })
    roads.value = res.items
    roadsTotal.value = res.total
  } finally {
    roadsLoading.value = false
  }
}

fetchRoads()
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2>系统管理</h2>
    </div>

    <!-- 数据采集：配置参数后点击触发，后台异步执行 -->
    <el-card shadow="never" style="margin-bottom: 16px;">
      <template #header>
        <span style="font-weight: 600;">数据采集</span>
      </template>
      <el-form :inline="true" label-width="100px">
        <el-form-item label="起始页码">
          <el-input-number v-model="fetchForm.start_page" :min="1" :max="20000" style="width: 140px;" />
        </el-form-item>
        <el-form-item label="采集页数">
          <el-input-number v-model="fetchForm.max_pages" :min="1" :max="20000" :step="100" style="width: 140px;" />
        </el-form-item>
        <el-form-item label="每页条数">
          <el-select v-model="fetchForm.rows_per_page" style="width: 120px;">
            <el-option :label="500" :value="500" />
            <el-option :label="1000" :value="1000" />
            <el-option :label="2000" :value="2000" />
            <el-option :label="5000" :value="5000" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="triggerFetch" :loading="fetchLoading" :icon="'Download'">
            触发采集
          </el-button>
        </el-form-item>
      </el-form>
      <div style="margin-top: 8px; color: #909399; font-size: 13px;">
        预计采集: {{ (fetchForm.max_pages * fetchForm.rows_per_page).toLocaleString() }} 条
        (第 {{ fetchForm.start_page }} ~ {{ fetchForm.start_page + fetchForm.max_pages - 1 }} 页)
        &nbsp;|&nbsp; 数据集总量: 10,174,000 条
        &nbsp;|&nbsp; 总页数: {{ Math.ceil(10174000 / fetchForm.rows_per_page).toLocaleString() }} 页
      </div>
      <el-alert
        v-if="fetchResult"
        :title="fetchResult.message"
        type="success"
        :closable="true"
        show-icon
        style="margin-top: 12px;"
      />
      <el-alert
        type="info"
        :closable="false"
        show-icon
        style="margin-top: 12px;"
      >
        <template #title>
          <div>
            <b>说明:</b> 数据来自深圳开放数据平台静态样例（2018-04 ~ 2019-06），共约1017万条。
            采集任务在后台异步执行，每页耗时约1秒。支持断点续采：记录上次最后页码，下次从该页开始。
          </div>
        </template>
      </el-alert>
    </el-card>

    <!-- 路段信息 -->
    <el-card shadow="never">
      <template #header>
        <span style="font-weight: 600;">路段信息 (共 {{ roadsTotal }} 条)</span>
      </template>
      <el-table :data="roads" v-loading="roadsLoading" stripe border>
        <el-table-column prop="roadsect_id" label="路段ID" width="180" />
      </el-table>
      <div style="display: flex; justify-content: flex-end; margin-top: 16px;">
        <el-pagination
          v-model:current-page="roadsPage"
          :page-size="50"
          :total="roadsTotal"
          layout="total, prev, pager, next"
          @current-change="fetchRoads"
        />
      </div>
    </el-card>
  </div>
</template>
