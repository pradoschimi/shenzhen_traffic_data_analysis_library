<script setup>
/**
 * 数据查询页：用表格展示速度记录，支持日期/路段ID/高峰类型筛选和分页。
 */
import { ref, reactive, onMounted } from 'vue'
import { trafficApi } from '../api'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const tableData = ref([])
const total = ref(0)

const query = reactive({
  start_date: '',
  end_date: '',
  roadsect_id: '',
  peak_type: '',
  page: 1,
  page_size: 20,
})

const dateRange = ref([])

async function fetchData() {
  loading.value = true
  try {
    if (dateRange.value && dateRange.value.length === 2) {
      query.start_date = dateRange.value[0]
      query.end_date = dateRange.value[1]
    } else {
      query.start_date = ''
      query.end_date = ''
    }
    const res = await trafficApi.getRecords(query)
    tableData.value = res.items
    total.value = res.total
  } catch (err) {
    // 拦截器已经处理了错误提示
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  query.page = 1
  fetchData()
}

function handlePageChange(page) {
  query.page = page
  fetchData()
}

function handleSizeChange(size) {
  query.page_size = size
  query.page = 1
  fetchData()
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2>数据查询</h2>
    </div>

    <!-- 搜索条件栏 -->
    <el-card shadow="never" style="margin-bottom: 16px;">
      <el-form :inline="true" @submit.prevent="handleSearch">
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="起始"
            end-placeholder="结束"
            value-format="YYYY-MM-DD"
            style="width: 240px;"
          />
        </el-form-item>
        <el-form-item label="路段ID">
          <el-input v-model="query.roadsect_id" placeholder="路段ID" clearable style="width: 150px;" />
        </el-form-item>
        <el-form-item label="高峰类型">
          <el-select v-model="query.peak_type" placeholder="全部" clearable style="width: 120px;">
            <el-option label="早高峰" value="早高峰" />
            <el-option label="晚高峰" value="晚高峰" />
            <el-option label="平峰" value="平峰" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :icon="'Search'">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格 -->
    <el-card shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe border style="width: 100%;">
        <el-table-column prop="roadsect_id" label="路段ID" width="120" />
        <el-table-column prop="record_date" label="日期" width="110" />
        <el-table-column prop="period" label="时段" width="80" />
        <el-table-column prop="avg_speed" label="平均速度(km/h)" width="140">
          <template #default="{ row }">
            <el-tag :type="row.avg_speed < 20 ? 'danger' : row.avg_speed < 40 ? 'warning' : 'success'" size="small">
              {{ row.avg_speed }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="go_count" label="通行车次" width="100" />
        <el-table-column prop="go_time" label="通行时间(s)" width="110" />
        <el-table-column prop="go_len" label="通行距离(m)" width="110" />
        <el-table-column prop="peak_type" label="高峰类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.peak_type === '早高峰' ? 'warning' : row.peak_type === '晚高峰' ? 'danger' : 'info'" size="small">
              {{ row.peak_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_workday" label="工作日" width="80">
          <template #default="{ row }">
            {{ row.is_workday ? '是' : '否' }}
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div style="display: flex; justify-content: flex-end; margin-top: 16px;">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>
