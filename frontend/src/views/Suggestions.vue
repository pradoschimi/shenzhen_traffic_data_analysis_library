<script setup>
/**
 * 交通建议页：查看已提交的建议列表，支持提交新建议。
 */
import { ref, reactive, onMounted } from 'vue'
import { userApi } from '../api'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const suggestions = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)

const form = reactive({
  title: '',
  content: '',
  roadsect_id: '',
})

async function fetchSuggestions() {
  loading.value = true
  try {
    const res = await userApi.getSuggestions({ page: page.value, page_size: pageSize.value })
    suggestions.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function submitSuggestion() {
  if (!form.title || !form.content) {
    ElMessage.warning('请填写标题和内容')
    return
  }
  try {
    await userApi.createSuggestion(form)
    ElMessage.success('建议提交成功')
    dialogVisible.value = false
    form.title = ''
    form.content = ''
    form.roadsect_id = ''
    fetchSuggestions()
  } catch (err) {
    // 已由拦截器处理
  }
}

onMounted(() => fetchSuggestions())
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2>交通建议</h2>
      <el-button type="primary" @click="dialogVisible = true" :icon="'EditPen'">提交建议</el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="suggestions" v-loading="loading" stripe border>
        <el-table-column type="index" label="#" width="60" />
        <el-table-column prop="title" label="标题" min-width="150" />
        <el-table-column prop="content" label="内容" min-width="250" show-overflow-tooltip />
        <el-table-column prop="roadsect_id" label="路段ID" width="120" />
        <el-table-column prop="created_at" label="提交时间" width="180">
          <template #default="{ row }">
            {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '' }}
          </template>
        </el-table-column>
      </el-table>

      <div style="display: flex; justify-content: flex-end; margin-top: 16px;">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchSuggestions"
        />
      </div>

      <el-empty v-if="!loading && suggestions.length === 0" description="暂无建议" />
    </el-card>

    <!-- 提交建议的弹窗 -->
    <el-dialog v-model="dialogVisible" title="提交交通建议" width="520px">
      <el-form label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="建议标题" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="路段ID">
          <el-input v-model="form.roadsect_id" placeholder="相关路段ID（选填）" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="5"
            placeholder="请详细描述您的建议..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitSuggestion">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>
