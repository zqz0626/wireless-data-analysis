<template>
  <div class="data-manage-container">
    <h1>数据管理</h1>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>文件上传</span>
        </div>
      </template>
      
      <!-- 单文件上传模式 -->
      <div>
        <el-upload
          class="upload-demo"
          drag
          action=""
          :http-request="handleUpload"
          :before-upload="beforeUpload"
          :on-success="onUploadSuccess"
          :on-error="onUploadError"
          :limit="1"
          :file-list="uploadFileList"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            点击或拖拽文件到此处上传
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持CSV、Excel(xlsx, xls)、GeoJSON格式文件，单个文件大小不超过100MB
            </div>
          </template>
        </el-upload>
      </div>
    </el-card>

    <!-- 文件列表 -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>文件列表</span>
        </div>
      </template>
      <el-table :data="displayFileList" style="width: 100%" row-key="id" highlight-current-row @row-click="onRowClick">
        <el-table-column prop="original_filename" label="文件名" min-width="200">
          <template #default="scope">
            <span class="file-name" @dblclick="onNameDblClick(scope.row, $event)" :title="scope.row.original_filename">
              {{ scope.row.original_filename }}
            </span>
            <el-tooltip :content="tooltipText[scope.row.id] || '复制文件名'" placement="top">
              <span class="copy-icon" role="button" tabindex="0" @click.stop.prevent="copyFileName(scope.row)" title="复制文件名">
                <!-- 简单的剪贴板 SVG 图标（内联，避免额外依赖） -->
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
                  <path d="M16 1H8a2 2 0 0 0-2 2v2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                  <rect x="8" y="5" width="11" height="14" rx="2" stroke="currentColor" stroke-width="1.6"/>
                  <path d="M16 9H12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
                </svg>
              </span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="120">
          <template #default="scope">
            {{ scope && scope.row ? formatFileSize(scope.row.size) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="extension" label="格式" width="100" />
        <el-table-column label="类型" width="120">
          <template #default="scope">
            {{ getFileRole(scope.row) }}
          </template>
        </el-table-column>
        <el-table-column prop="upload_time" label="上传时间" width="180">
          <template #default="scope">
            {{ scope && scope.row ? formatDateTime(scope.row.upload_time) : '-' }}
          </template>
        </el-table-column>
        <!-- 操作列已移除，使用表格外的工具栏进行操作 -->
      </el-table>

      <!-- 操作工具栏：选择文件后启用 -->
      <div class="action-toolbar" aria-hidden="false">
        <div class="action-info">
          <template v-if="selectedFile">
            <div class="selected-card">
              <div class="file-icon" aria-hidden>📄</div>
              <div class="file-meta">
                <div class="selected-name" :title="selectedFile.original_filename">{{ selectedFile.original_filename }}</div>
                <div class="selected-meta">{{ formatFileSize(selectedFile.size) }} · {{ selectedFile.extension }}</div>
              </div>
            </div>
          </template>
          <template v-else>
            <div class="selected-card empty">
              <div class="file-icon" aria-hidden>📁</div>
              <div class="file-meta">
                <div class="selected-name">未选择文件</div>
                <div class="selected-meta">请选择一行以启用操作</div>
              </div>
            </div>
          </template>
        </div>
        <div class="action-buttons">
          <el-button class="pill-btn preview" size="small" :disabled="!selectedFile" @click="previewSelected">
            <span class="btn-icon">🔍</span>
            <span class="btn-text">预览</span>
          </el-button>

          <el-button class="pill-btn edit" size="small" :disabled="!selectedFile" @click="openEditDialog(selectedFile)">
            <span class="btn-icon">✏️</span>
            <span class="btn-text">编辑</span>
          </el-button>

          <el-button class="pill-btn download" size="small" :disabled="!selectedFile" @click="downloadSelected">
            <span class="btn-icon">⬇️</span>
            <span class="btn-text">下载</span>
          </el-button>

          <el-button class="pill-btn delete" size="small" :disabled="!selectedFile" @click="deleteSelected">
            <span class="btn-icon">🗑️</span>
            <span class="btn-text">删除</span>
          </el-button>
        </div>
      </div>
      
      <!-- 文件列表分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="filePage.current"
          v-model:page-size="filePage.size"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="fileTotal"
          @size-change="handleFileSizeChange"
          @current-change="handleFileCurrentChange"
        />
      </div>
    </el-card>

    <!-- 编辑显示名对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑文件显示名" :before-close="closeEditDialog">
      <div>
        <el-form>
          <el-form-item label="当前文件ID">
            <div>{{ editFileId }}</div>
          </el-form-item>
          <el-form-item label="显示名">
            <el-input v-model="editFileName" placeholder="请输入新的显示名" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeEditDialog">取消</el-button>
          <el-button type="primary" @click="saveEditFileName">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 预览对话框 -->
    <el-dialog
      v-model="previewDialogVisible"
      title="文件预览"
      :width="'80%'"
      :before-close="closePreviewDialog"
    >
      <div v-if="previewData">
        <div class="preview-header mb-4">
          <h3>{{ previewData.file_info?.original_filename }}</h3>
          <p class="text-gray-500">总条数: {{ previewData.total_rows }}, 格式: {{ previewData.file_info?.extension }}</p>
        </div>
        
        <el-table :data="previewData.data" style="width: 100%" :max-height="400">
          <template v-for="col in previewData.columns" :key="col">
            <el-table-column :prop="col" :label="col" />
          </template>
        </el-table>
        
        <!-- 预览分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="previewPage.current"
            v-model:page-size="previewPage.size"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="previewData.total_rows || 0"
            @size-change="handlePreviewSizeChange"
            @current-change="handlePreviewCurrentChange"
          />
        </div>
      </div>
      <div v-else class="text-center py-4">
        <div class="loading-text">加载中...</div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import api from '../api/index'
import { UploadFilled } from '@element-plus/icons-vue'

/**
 * 数据管理组件
 * 用于上传、管理和操作数据文件，支持单文件和多文件关联上传
 * 提供文件预览、编辑、下载和删除等功能
 */
export default {
  name: 'DataManage',
  components: {
    UploadFilled
  },
  setup() {
    // 文件上传相关
    const uploadFileList = ref([])
    
    // 文件列表相关
    const fileListData = ref([])
    const fileTotal = ref(0)
    const filePage = ref({
      current: 1,
      size: 10
    })
    
    // 文件列表直接使用原始数据，按上传时间倒序排序
    const displayFileList = computed(() => {
      const files = fileListData.value || []
      return files
    })

    // 预览相关
    const previewDialogVisible = ref(false)
    const previewData = ref(null)
    const currentPreviewFileId = ref('')
    const previewPage = ref({
      current: 1,
      size: 20
    })

    // 编辑显示名相关
    const editDialogVisible = ref(false)
    const editFileId = ref('')
    const editFileName = ref('')
    
    // 选中行（用于表格外工具栏）
    const selectedFile = ref(null)
    // tooltip 文案缓存（按文件 id 记录）
    const tooltipText = reactive({})
    
    // 格式化文件大小
    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }
    
    // 格式化日期时间
    const formatDateTime = (dateTimeStr) => {
      if (!dateTimeStr) return ''
      const date = new Date(dateTimeStr)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    }

    // 获取文件图标
    const getFileIcon = (fileName) => {
      const extension = fileName.split('.').pop().toLowerCase()
      if (['csv', 'xlsx', 'xls'].includes(extension)) {
        return '📊'
      } else if (['geojson', 'json'].includes(extension)) {
        return '🗺️'
      } else {
        return '📄'
      }
    }

    // 获取文件类型
    const getFileType = (fileName) => {
      const extension = fileName.split('.').pop().toLowerCase()
      if (['csv', 'xlsx', 'xls'].includes(extension)) {
        return '数据文件'
      } else if (['geojson', 'json'].includes(extension)) {
        return '地理边界文件'
      } else {
        return '其他文件'
      }
    }

    // 根据后端的 file_type 字段返回文件角色
    const getFileRole = (row) => {
      if (!row) return ''
      if (row.file_type === 'data') return '数据文件'
      if (row.file_type === 'geojson') return '地理边界文件'
      return '其他'
    }
    
    // 单文件上传前校验
    const beforeUpload = (file) => {
      const allowedExtensions = ['csv', 'xlsx', 'xls', 'geojson', 'json']
      const extension = file.name.split('.').pop().toLowerCase()
      const isAllowedType = allowedExtensions.includes(extension)
      const isLt100M = file.size / 1024 / 1024 < 100
      
      if (!isAllowedType) {
        ElMessage.error('只支持CSV、Excel、GeoJSON格式文件！')
        return false
      }
      if (!isLt100M) {
        ElMessage.error('文件大小不能超过100MB！')
        return false
      }

      // 简单前端校验：当前列表中已存在同名文件时禁止上传
      const existingNames = (fileListData.value || []).map(f => f.original_filename)
      if (existingNames.includes(file.name)) {
        ElMessage.error('已存在同名文件，请先删除或重命名后再上传')
        return false
      }
      
      return true
    }
    
    // 处理单文件上传
    const handleUpload = async (options) => {
      const { file } = options
      try {
        const response = await api.file.uploadFile(file)
        if (response.success) {
          options.onSuccess(response)
        } else {
          options.onError(new Error(response.message || '上传失败'))
        }
      } catch (error) {
        options.onError(error)
      }
    }
    
    // 上传成功处理
    const onUploadSuccess = (response) => {
      const msg = (response && response.message) || '文件上传成功'
      ElMessage.success(msg)
      uploadFileList.value = []
      // 重新加载文件列表
      loadFileList()
    }
    
    // 上传失败处理
    const onUploadError = (error) => {
      ElMessage.error(error.message || '文件上传失败')
    }
    
    // 加载文件列表
    const loadFileList = async () => {
      try {
        const response = await api.file.getFileList(filePage.value.current, filePage.value.size)
        if (response.success) {
          fileListData.value = response.data.files || []
          fileTotal.value = response.data.total || 0
        }
      } catch (error) {
        ElMessage.error('获取文件列表失败')
        console.error('获取文件列表失败:', error)
      }
    }
    
    // 文件列表分页处理
    const handleFileSizeChange = (size) => {
      filePage.value.size = size
      loadFileList()
    }
    
    const handleFileCurrentChange = (current) => {
      filePage.value.current = current
      loadFileList()
    }
    
    // 预览文件
    const previewFile = async (fileId) => {
      currentPreviewFileId.value = fileId
      previewPage.value.current = 1
      previewData.value = null
      previewDialogVisible.value = true
      
      await loadPreviewData()
    }
    
    // 加载预览数据
    const loadPreviewData = async () => {
      if (!currentPreviewFileId.value) return
      
      try {
        const response = await api.file.previewFile(
          currentPreviewFileId.value,
          previewPage.value.current,
          previewPage.value.size
        )
        if (response.success) {
          previewData.value = response.data
        }
      } catch (error) {
        if (error?.error === 'HTTP_404') {
          ElMessage.warning('文件不存在或已被删除，已为你刷新列表')
          // 关闭预览并刷新列表
          previewDialogVisible.value = false
          previewData.value = null
          currentPreviewFileId.value = ''
          selectedFile.value = null
          await loadFileList()
          return
        }
        ElMessage.error(error?.message || '获取文件预览失败')
        console.error('获取文件预览失败:', error)
      }
    }
    
    // 预览分页处理
    const handlePreviewSizeChange = (size) => {
      previewPage.value.size = size
      loadPreviewData()
    }
    
    const handlePreviewCurrentChange = (current) => {
      previewPage.value.current = current
      loadPreviewData()
    }
    
    // 关闭预览对话框
    const closePreviewDialog = () => {
      previewDialogVisible.value = false
      previewData.value = null
      currentPreviewFileId.value = ''
    }

    // 行点击选择处理
    const onRowClick = (row) => {
      selectedFile.value = row || null
    }

    // 双击文件名：若按住 Ctrl/Meta/Alt/Shift 则复制文件名，否则打开预览（详情）
    const onNameDblClick = async (row, event) => {
      if (!row) return
      const name = row.original_filename || ''
      const modifierPressed = event.ctrlKey || event.metaKey || event.altKey || event.shiftKey
      if (modifierPressed) {
        // 复制文件名到剪贴板
        try {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(name)
          } else {
            // 兼容性回退
            const ta = document.createElement('textarea')
            ta.value = name
            document.body.appendChild(ta)
            ta.select()
            document.execCommand('copy')
            document.body.removeChild(ta)
          }
          ElMessage.success('文件名已复制到剪贴板')
        } catch (err) {
          console.error('复制文件名失败', err)
          ElMessage.error('复制失败')
        }
      } else {
        // 打开预览详情
        await previewFile(row.id)
      }
    }

    // 工具栏操作（基于 selectedFile）
    const previewSelected = async () => {
      if (!selectedFile.value) return
      await previewFile(selectedFile.value.id)
    }

    const downloadSelected = async () => {
      if (!selectedFile.value) return
      downloadFile(selectedFile.value.id)
    }

    const deleteSelected = async () => {
      if (!selectedFile.value) return
      await deleteFile(selectedFile.value.id)
      selectedFile.value = null
      // 重新加载文件列表
      await loadFileList()
    }

    // 复制文件名（用于右侧复制图标），复制后短暂在 tooltip 上显示已复制
    const copyFileName = async (row) => {
      if (!row) return
      const name = row.original_filename || ''
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(name)
        } else {
          const ta = document.createElement('textarea')
          ta.value = name
          document.body.appendChild(ta)
          ta.select()
          document.execCommand('copy')
          document.body.removeChild(ta)
        }
        // 使用局部 tooltip 显示已复制，而不是全局消息
        tooltipText[row.id] = '已复制'
        setTimeout(() => {
          // 回退到默认文案
          tooltipText[row.id] = '复制文件名'
        }, 1200)
      } catch (err) {
        console.error('复制文件名失败', err)
        ElMessage.error('复制失败')
      }
    }

    // 打开编辑对话框
    const openEditDialog = (row) => {
      if (!row || !row.id) return
      editFileId.value = row.id
      editFileName.value = row.original_filename || ''
      editDialogVisible.value = true
    }

    const closeEditDialog = () => {
      editDialogVisible.value = false
      editFileId.value = ''
      editFileName.value = ''
    }

    // 保存编辑后的名称
    const saveEditFileName = async () => {
      if (!editFileId.value) {
        ElMessage.error('无效的文件ID')
        return
      }
      if (!editFileName.value || editFileName.value.trim() === '') {
        ElMessage.error('显示名不能为空')
        return
      }

      try {
        const response = await api.file.renameFile(editFileId.value, editFileName.value.trim())
        if (response.success) {
          ElMessage.success(response.message || '文件显示名更新成功')
          closeEditDialog()
          // 刷新文件列表
          loadFileList()
        }
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || error.message || '更新失败')
        console.error('更新显示名失败:', error)
      }
    }
    
    // 下载文件
    const downloadFile = async (fileId) => {
      try {
        // 使用相对路径通过代理下载
        window.open(`/api/files/${fileId}/download`, '_blank')
      } catch (error) {
        ElMessage.error('文件下载失败')
        console.error('文件下载失败:', error)
      }
    }
    
    // 删除文件
    const deleteFile = async (fileId, showConfirm = true) => {
      // 添加参数检查，防止undefined访问
      if (!fileId) {
        ElMessage.error('无效的文件ID')
        return
      }
      
      // 只有在需要显示确认对话框且showConfirm为true时才显示
      if (showConfirm) {
        const confirmed = await ElMessageBox.confirm(
          '确定要删除这个文件吗？',
          '删除确认',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        ).catch(() => false)
        
        if (!confirmed) return
      }
      
      try {
        const response = await api.file.deleteFile(fileId)
        if (response.success) {
          ElMessage.success(response.message || '文件删除成功')
        }
      } catch (error) {
        ElMessage.error('文件删除失败')
        console.error('文件删除失败:', error)
      }
    }
    

    
    // 组件挂载时加载文件列表
    onMounted(() => {
      loadFileList()
      window.addEventListener('files:updated', onFilesUpdated)
    })

    const onFilesUpdated = () => {
      loadFileList()
    }

    onUnmounted(() => {
      window.removeEventListener('files:updated', onFilesUpdated)
    })
    
    return {
      // 文件上传
      uploadFileList,
      beforeUpload,
      handleUpload,
      onUploadSuccess,
      onUploadError,
      getFileIcon,
      getFileType,
      getFileRole,
      
      // 文件列表
      fileListData,
      displayFileList,
      fileTotal,
      filePage,
      formatFileSize,
      formatDateTime,
      handleFileSizeChange,
      handleFileCurrentChange,
      
      // 预览相关
      previewDialogVisible,
      previewData,
      previewPage,
      previewFile,
      handlePreviewSizeChange,
      handlePreviewCurrentChange,
      closePreviewDialog,

      // 行选择与工具栏
      selectedFile,
      onRowClick,
      onNameDblClick,
      tooltipText,
      copyFileName,
      previewSelected,
      downloadSelected,
      deleteSelected,
      
      // 编辑显示名相关
      editDialogVisible,
      editFileId,
      editFileName,
      openEditDialog,
      closeEditDialog,
      saveEditFileName,
      
      // 文件操作
      downloadFile,
      deleteFile
    }
  }
}
</script>

<style scoped>
.data-manage-container {
  padding: 20px;
}

/* 增加卡片之间的垂直间距，使上传区域与文件列表之间空隙更明显 */
.data-manage-container > :deep(.el-card) {
  margin-bottom: 32px;
}

.data-manage-container h1 {
  margin-bottom: 30px;
  color: #303133;
  font-size: 24px;
  font-weight: 600;
}

.loading-text {
  font-size: 16px;
  color: #606266;
  padding: 20px 0;
  text-align: center;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #303133;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.preview-header {
  margin-bottom: 20px;
}

.preview-header h3 {
  margin-bottom: 8px;
  color: #303133;
}

.text-gray-500 {
  color: #606266;
  font-size: 14px;
}

:deep(.el-upload-dragger) {
  width: 100% !important;
  border-radius: 8px;
  transition: all 0.3s;
}

:deep(.el-upload-dragger:hover) {
  border-color: #1890ff;
  box-shadow: 0 0 10px rgba(24, 144, 255, 0.2);
}

/* 表格样式优化 */
:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-table__header) {
  background-color: var(--page-inner-bg);
}

:deep(.el-table__header th) {
  background-color: var(--page-inner-bg) !important;
  font-weight: 600;
  color: #303133;
}

/* 操作按钮样式 */
.pill-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: auto;
  height: 36px;
  padding: 6px 12px;
  box-sizing: border-box;
  border-radius: 10px;
  background: #fff;
  border: 1px solid rgba(16,24,40,0.06);
  box-shadow: 0 1px 6px rgba(16,24,40,0.04);
  color: #1f2d3d;
  font-weight: 600;
}

/* 批量操作按钮样式 */
.batch-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.batch-actions .btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
}

.batch-actions .btn-text {
  font-size: 13px;
  font-weight: 600;
}

.pill-btn .btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
}

.pill-btn.preview { background: linear-gradient(180deg, rgba(194, 122, 59, 0.1), #ffffff); border-color: var(--primary-color); }
.pill-btn.edit { background: linear-gradient(180deg, rgba(194, 122, 59, 0.1), #ffffff); border-color: var(--primary-color); }
.pill-btn.download { background: linear-gradient(180deg, rgba(194, 122, 59, 0.1), #ffffff); border-color: var(--primary-color); }
.pill-btn.delete { background: linear-gradient(180deg, rgba(194, 122, 59, 0.1), #ffffff); border-color: var(--primary-color); }
.pill-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(16,24,40,0.08); }

/* 操作工具栏样式：水平四个按钮，紧凑显示 */
.action-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-top: 1px solid var(--border-color, #f5f7fa);
  margin-top: 12px;
  gap: 12px;
}
.action-info {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 240px;
}
.selected-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 10px;
  background: linear-gradient(180deg, #ffffff, #fbfdff);
  box-shadow: 0 6px 18px rgba(16,24,40,0.06);
  border: 1px solid rgba(16,24,40,0.04);
}
.selected-card.empty {
  background: transparent;
  box-shadow: none;
  border: 1px dashed rgba(16,24,40,0.04);
}
.file-icon {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  background: linear-gradient(180deg,#f6f9ff,#ffffff);
  border-radius: 8px;
}
.file-meta {
  display: flex;
  flex-direction: column;
}
.selected-name {
  font-weight: 700;
  color: #1f2d3d;
  font-size: 14px;
  max-width: 360px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.selected-meta {
  color: #6b7280;
  font-size: 13px;
}
.file-name {
  cursor: pointer;
  color: #1f2d3d;
  font-weight: 600;
}
.file-name:hover { text-decoration: underline; }
.copy-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-left: 8px;
  font-size: 14px;
  color: #6b7280;
  cursor: pointer;
}
.copy-icon:hover { color: #1f2d3d; }
.action-buttons {
  display: flex;
  gap: 10px;
  align-items: center;
}
/* 在工具栏中覆盖 .pill-btn 使其为紧凑的横向按钮 */
.action-toolbar .pill-btn {
  width: auto; /* 不占满容器 */
  min-width: 84px;
  height: 32px;
  padding: 4px 10px;
  font-size: 13px;
}

/* 多文件上传预览样式 */
.selected-files-preview {
  margin-top: 20px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.selected-files-preview h4 {
  margin: 0 0 12px 0;
  color: #495057;
  font-size: 14px;
  font-weight: 600;
}

.file-preview-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-preview-item {
  display: flex;
  align-items: center;
  padding: 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #dee2e6;
  gap: 12px;
}

.file-preview-item .file-icon {
  font-size: 20px;
  width: 32px;
  text-align: center;
}

.file-preview-item .file-info {
  flex: 1;
}

.file-preview-item .file-name {
  font-weight: 600;
  color: #212529;
  font-size: 14px;
}

.file-preview-item .file-size {
  color: #6c757d;
  font-size: 12px;
}

.file-preview-item .file-type {
  font-size: 12px;
  color: #28a745;
  font-weight: 600;
  padding: 4px 8px;
  background: #d4edda;
  border-radius: 4px;
}

/* 窄屏（如左右分屏）下整体收紧边距并调整工具栏布局，断点与其它页面保持一致 */
@media screen and (max-width: 768px) {
  .data-manage-container {
    padding: 10px;
  }

  .action-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .action-buttons {
    flex-wrap: wrap;
    justify-content: space-between;
  }

  .selected-name {
    max-width: 260px;
  }
}

@media (max-width: 600px) {
  .action-toolbar { flex-direction: column; align-items: stretch; }
  .action-buttons { justify-content: space-between; }
  .action-info { order: 2; }
  
  .file-preview-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .file-preview-item .file-type {
    align-self: flex-end;
  }
}
</style>
