 <template>
  <div class="preprocess-container">
    <h1>数据预处理配置</h1>
    
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>数据源选择</span>
        </div>
      </template>
      <div class="data-source-selector horizontal">
        <el-select v-model="selectedFileId" placeholder="输入或选择要处理的数据文件" class="ds-select" filterable>
          <el-option
            v-for="file in availableFiles"
            :key="file.id"
            :label="file.original_filename"
            :value="file.id"
          >
            <div class="option-content">
              <span>{{ file.original_filename }}</span>
              <small class="text-gray-500">{{ formatFileSize(file.size) }} · {{ file.extension.toUpperCase() }}</small>
            </div>
          </el-option>
        </el-select>
        <el-button type="primary" @click="loadFileInfo" :disabled="!selectedFileId" class="ds-button">
          加载文件信息
        </el-button>
      </div>
    </el-card>

    <el-card shadow="never" v-if="fileInfo">
      <template #header>
        <div class="card-header">
          <span>文件信息</span>
        </div>
      </template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="文件名">{{ fileInfo.original_filename }}</el-descriptions-item>
        <el-descriptions-item label="文件大小">{{ formatFileSize(fileInfo.size) }}</el-descriptions-item>
        <el-descriptions-item label="文件格式">{{ fileInfo.extension.toUpperCase() }}</el-descriptions-item>
        <el-descriptions-item label="上传时间">{{ formatDateTime(fileInfo.upload_time) }}</el-descriptions-item>
        <el-descriptions-item label="数据行数">{{ fileInfo.row_count || '未知' }}</el-descriptions-item>
        <el-descriptions-item label="数据列数">{{ fileInfo.column_count || '未知' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" class="mb-4" v-if="fileInfo">
      <template #header>
        <div class="card-header">
          <span>预处理配置</span>
        </div>
      </template>
      
      <el-collapse v-model="activeCollapseNames" class="config-collapse">
        <el-collapse-item title="基础处理" name="basic" v-if="false">
          <div class="config-section">
            <el-checkbox v-model="preprocessConfig.skipHeader">跳过表头</el-checkbox>
            <el-checkbox v-model="preprocessConfig.removeDuplicates">删除重复行</el-checkbox>
            <el-checkbox v-model="preprocessConfig.trimWhitespace">去除空白字符</el-checkbox>
          </div>
        </el-collapse-item>
        
        <el-collapse-item title="缺失值处理" name="missing">
          <div class="config-section">
            <div class="strategy-input-container">
              <el-select v-model="preprocessConfig.missingValueStrategy" placeholder="选择缺失值处理方式" style="width: 280px">
                <el-option label="跳过缺失值 - 忽略含有缺失值的行" value="skip"></el-option>
                <el-option label="均值填充 - 使用该列的平均值填充" value="mean"></el-option>
                <el-option label="中位数填充 - 使用该列的中位数填充" value="median"></el-option>
                <el-option label="常量填充 - 使用指定常量值填充" value="constant"></el-option>
              </el-select>
              
              <el-input 
                v-if="preprocessConfig.missingValueStrategy === 'constant'" 
                v-model="preprocessConfig.constantValue" 
                placeholder="请输入填充常量" 
                style="width: 280px;"
              />
            </div>
            
            <div class="mt-3">
              <div class="select-all-container">
                <el-checkbox
                  v-model="isAllMissingColumnsSelected"
                  @change="handleMissingColumnsSelectAll"
                  size="small"
                >
                  全选
                </el-checkbox>
                <el-input
                  v-model="missingColumnSearchKeyword"
                  size="small"
                  placeholder="搜索列名"
                  clearable
                  class="area-search-input"
                />
              </div>
              <div class="feature-list">
                <el-checkbox-group v-model="preprocessConfig.missingValueColumns" @change="handleMissingColumnsSelect">
                  <el-checkbox
                    v-for="col in filteredMissingColumns"
                    :key="col"
                    :label="col"
                    size="small"
                    class="feature-checkbox"
                  >
                    {{ col }}
                  </el-checkbox>
                </el-checkbox-group>
              </div>
              <div class="selected-features-display" v-if="preprocessConfig.missingValueColumns.length > 0">
                <span class="selection-label">已选择列：</span>
                <el-tag
                  v-for="col in displayedMissingTags"
                  :key="col"
                  closable
                  @close="removeMissingColumn(col)"
                  size="small"
                  :title="col"
                  class="feature-tag"
                >
                  {{ col }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-collapse-item>
        
        <el-collapse-item title="异常值处理" name="outliers" v-if="false">
          <div class="config-section">
            <div class="mb-2">
              <el-select v-model="preprocessConfig.outlierMethod" placeholder="选择异常值检测方法">
                <el-option label="IQR方法" value="iqr" />
              </el-select>
            </div>
            
            <div class="mb-2">
              <el-input-number
                v-model="preprocessConfig.outlierThreshold"
                :min="1"
                :max="5"
                :step="0.5"
                label="阈值"
                placeholder="阈值（1.5-3.0之间较常用）"
              />
            </div>
            
            <div class="mb-3">
              <el-radio-group v-model="preprocessConfig.outlierAction" size="large">
                <el-radio-button label="clip">截断异常值</el-radio-button>
                <el-radio-button label="remove">删除异常值</el-radio-button>
              </el-radio-group>
            </div>
            
            <div class="mt-3">
              <div class="select-all-container">
                <el-checkbox
                  v-model="isAllOutlierColumnsSelected"
                  @change="handleOutlierColumnsSelectAll"
                  size="small"
                >
                  全选
                </el-checkbox>
              </div>
              <div class="feature-list">
                <el-checkbox-group v-model="preprocessConfig.outlierColumns" @change="handleOutlierColumnsSelect">
                  <el-checkbox
                    v-for="col in fileInfo?.columns || []"
                    :key="col"
                    :label="col"
                    size="small"
                    class="feature-checkbox"
                  >
                    {{ col }}
                  </el-checkbox>
                </el-checkbox-group>
              </div>
              <div class="selected-features-display" v-if="preprocessConfig.outlierColumns.length > 0">
                <span class="selection-label">已选择列：</span>
                <el-tag
                  v-for="col in preprocessConfig.outlierColumns"
                  :key="col"
                  closable
                  @close="removeOutlierColumn(col)"
                  size="small"
                  :title="col"
                  class="feature-tag"
                >
                  {{ col }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-collapse-item>
        
        <el-collapse-item title="数据标准化" name="transform">
          <div class="config-section">
            <div v-if="preprocessConfig.normalize" class="mt-2 mb-3 normalize-row">
              <el-select v-model="preprocessConfig.normalizeMethod" placeholder="选择标准化方法" class="normalize-method-select">
                <el-option label="Min-Max标准化" value="minmax" />
                <el-option label="Z-Score标准化" value="zscore" />
              </el-select>
              <div class="normalize-decimals">
                <span class="decimals-label">保留小数位：</span>
                <el-input-number
                  v-model="preprocessConfig.decimalPlaces"
                  :min="0"
                  :max="10"
                  :step="1"
                  size="small"
                />
              </div>
            </div>

            <!-- 标准化列选择（仅数值列） -->
            <div v-if="preprocessConfig.normalize" class="mt-2">
              <div class="select-all-container">
                <el-checkbox
                  v-model="isAllNormalizeColumnsSelected"
                  @change="handleNormalizeColumnsSelectAll"
                  size="small"
                >
                  标准化列全选（仅数值列）
                </el-checkbox>
                <el-tag size="small" type="info" class="ml-2">候选 {{ normalizeCandidates.length }} 列</el-tag>
                <el-input
                  v-model="normalizeColumnSearchKeyword"
                  size="small"
                  placeholder="搜索列名"
                  clearable
                  class="area-search-input"
                />
              </div>
              <div class="feature-list">
                <el-checkbox-group v-model="preprocessConfig.normalizeColumns" @change="handleNormalizeColumnsSelect">
                  <el-checkbox
                    v-for="col in filteredNormalizeColumns"
                    :key="col"
                    :label="col"
                    size="small"
                    class="feature-checkbox"
                  >
                    {{ col }}
                  </el-checkbox>
                </el-checkbox-group>
              </div>
              <div class="selected-features-display" v-if="preprocessConfig.normalizeColumns.length > 0">
                <span class="selection-label">已选择列：</span>
                <el-tag
                  v-for="col in displayedNormalizeTags"
                  :key="col"
                  closable
                  @close="removeNormalizeColumn(col)"
                  size="small"
                  :title="col"
                  class="feature-tag"
                >
                  {{ col }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-collapse-item>
        
        
      </el-collapse>
    </el-card>

    <el-card shadow="never" class="execute-card" v-if="fileInfo">
      <template #header>
        <div class="card-header">
          <span>执行预处理</span>
        </div>
      </template>
      <div class="action-buttons">
        <el-button size="large" @click="runPreprocess" :loading="isPreprocessing" :disabled="isPreprocessing">
          执行
        </el-button>
        <el-button size="large" @click="resetConfig">
          重置
        </el-button>
      </div>
    </el-card>

    <!-- 预处理结果对话框 -->
    <el-dialog
      v-model="resultDialogVisible"
      title="数据预处理结果"
      width="80%"
      :before-close="closeResultDialog"
      :close-on-click-modal="false"
    >
      <div v-if="preprocessResult">
        <div class="result-header mb-4">
          <h3>预处理完成</h3>
          <div class="text-gray-500">处理时间: {{ preprocessResult?.processing_time ? (preprocessResult.processing_time / 1000).toFixed(2) : '0.00' }} 秒</div>
        </div>
        
        <div class="result-stats mb-4">
          <h4 class="mb-2">数据统计信息</h4>
          <el-descriptions border :column="2">
            <el-descriptions-item label="原始数据行数">{{ preprocessResult?.stats?.original_rows || 0 }}</el-descriptions-item>
            <el-descriptions-item label="原始数据列数">{{ preprocessResult?.stats?.original_columns || 0 }}</el-descriptions-item>
            <el-descriptions-item label="处理后数据行数">{{ preprocessResult?.stats?.processed_rows || 0 }}</el-descriptions-item>
            <el-descriptions-item label="处理后数据列数">{{ preprocessResult?.stats?.processed_columns || 0 }}</el-descriptions-item>
            <el-descriptions-item label="数据变化" :span="2">
              <template #default>
                <el-tag :type="preprocessResult?.stats?.processed_rows < preprocessResult?.stats?.original_rows ? 'warning' : 'success'" size="small">
                  行数变化: {{ preprocessResult?.stats?.original_rows || 0 }} → {{ preprocessResult?.stats?.processed_rows || 0 }} 
                  ({{ preprocessResult?.stats?.original_rows ? ((preprocessResult.stats.processed_rows - preprocessResult.stats.original_rows) / preprocessResult.stats.original_rows * 100).toFixed(2) : 0 }}%)
                </el-tag>
              </template>
            </el-descriptions-item>
            <el-descriptions-item label="应用操作数量">{{ preprocessResult?.stats?.operations_applied || 0 }}</el-descriptions-item>
            <el-descriptions-item label="删除重复行数">{{ preprocessResult?.stats?.duplicates_removed || 0 }}</el-descriptions-item>
            <el-descriptions-item label="处理缺失值数量">{{ preprocessResult?.stats?.missing_values_handled || 0 }}</el-descriptions-item>
            <el-descriptions-item label="删除异常值数量">{{ preprocessResult?.stats?.outliers_removed || 0 }}</el-descriptions-item>
            <el-descriptions-item label="截断异常值数量">{{ preprocessResult?.stats?.outliers_clipped || 0 }}</el-descriptions-item>
            <el-descriptions-item label="选择特征数量">{{ preprocessResult?.stats?.features_selected || 0 }}</el-descriptions-item>
          </el-descriptions>
        </div>
        
        <!-- 数据质量信息 -->
        <div v-if="preprocessResult?.statistics?.data_quality || preprocessResult?.stats" class="result-stats mb-4">
          <h4 class="mb-2">数据质量指标</h4>
          <el-descriptions border :column="2">
            <el-descriptions-item label="完整度">{{ preprocessResult?.statistics?.data_quality?.completeness ? (preprocessResult.statistics.data_quality.completeness * 100).toFixed(1) : '100.0' }}%</el-descriptions-item>
            <el-descriptions-item label="数据有效性">{{ preprocessResult?.statistics?.data_quality?.validity ? (preprocessResult.statistics.data_quality.validity * 100).toFixed(1) : '100.0' }}%</el-descriptions-item>
          </el-descriptions>
        </div>
        
        <div class="mb-4">
          <h4 class="mb-2">处理后文件信息</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="文件ID">{{ preprocessResult.processed_file_id }}</el-descriptions-item>
          </el-descriptions>
        </div>
        
        <div class="sample-data" style="margin-top: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <h4 class="mb-2">处理后数据预览</h4>
            <div class="text-gray-500">
              显示 {{ Math.min(preprocessResult?.sample_data?.length || 0, 20) }} / {{ preprocessResult?.stats?.processed_rows || 0 }} 行
            </div>
          </div>
          
          <div style="overflow-x: auto;">
            <el-table 
              :data="preprocessResult.sample_data?.slice(0, 20) || []" 
              stripe 
              style="width: 100%" 
              :max-height="400"
            >
              <template v-if="preprocessResult.sample_data && preprocessResult.sample_data.length > 0">
                <el-table-column
                  v-for="col in Object.keys(preprocessResult.sample_data[0])"
                  :key="col"
                  :prop="col"
                  :label="col"
                  :show-overflow-tooltip="true"
                  min-width="120"
                >
                  <template #default="{row}">
                    <div v-if="typeof row[col] === 'number' && !isNaN(row[col]) && isFinite(row[col])" class="number-cell">
                      {{ row[col] }}
                    </div>
                    <div v-else-if="row[col] === 'NaN' || row[col] === '∞' || row[col] === '-∞'" class="special-value-cell">
                      {{ row[col] }}
                    </div>
                    <div v-else-if="row[col] === '-'" class="missing-value-cell">
                      {{ row[col] }}
                    </div>
                    <div v-else class="text-cell">
                      {{ row[col] }}
                    </div>
                  </template>
                </el-table-column>
              </template>
            </el-table>
          </div>
        </div>
      </div>
      <div v-else class="text-center py-4">
          <div class="loading-center">
            <el-icon><Loading /></el-icon>
            <div class="loading-text">正在加载数据...</div>
          </div>
        </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeResultDialog" plain>关闭</el-button>
          <el-button type="primary" @click="closeResultDialog">完成</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { ElMessage, ElLoading } from 'element-plus'
import api from '../api/index'
import { Loading } from '@element-plus/icons-vue'

/**
 * 数据预处理组件
 * 用于配置和执行数据预处理操作，包括缺失值处理、数据标准化等
 */
export default {
  name: 'Preprocess',
  components: {
    Loading
  },
  setup() {
    // 状态管理
    const selectedFileId = ref('') // 当前选中的文件ID
    const availableFiles = ref([]) // 可用文件列表
    const fileInfo = ref(null) // 当前文件信息
    const activeCollapseNames = ref([]) // 激活的折叠面板
    const resultDialogVisible = ref(false) // 结果对话框可见性
    const preprocessResult = ref(null) // 预处理结果
    const isPreprocessing = ref(false) // 预处理执行状态
    const isAllOutlierColumnsSelected = ref(false) // 异常值处理列全选状态
    const isAllMissingColumnsSelected = ref(false) // 缺失值处理列全选状态
    const isAllNormalizeColumnsSelected = ref(false) // 标准化列全选状态
    const dataTypes = ref({}) // 各列数据类型（来自后端）

    // 列搜索关键字
    const missingColumnSearchKeyword = ref('') // 缺失值处理列搜索关键字
    const normalizeColumnSearchKeyword = ref('') // 标准化列搜索关键字
    
    // 预处理配置
    const preprocessConfig = ref({
      skipHeader: false, // 是否跳过表头
      removeDuplicates: true, // 是否删除重复行
      trimWhitespace: true, // 是否去除空白字符
      missingValueStrategy: 'mean', // 缺失值处理策略
      missingValueColumns: [], // 缺失值处理列
      constantValue: '', // 常量填充值
      outlierMethod: 'iqr', // 异常值检测方法
      outlierThreshold: 1.5, // 异常值阈值
      outlierAction: 'clip', // 异常值处理动作
      outlierColumns: [], // 异常值处理列
      normalize: true, // 是否进行标准化
      normalizeMethod: 'zscore', // 标准化方法
      normalizeColumns: [], // 标准化列
      decimalPlaces: 7 // 保留小数位
    })
    
    /**
     * 格式化文件大小
     * @param {number} bytes - 文件大小（字节）
     * @returns {string} 格式化后的文件大小
     */
    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };
    
    /**
     * 格式化日期时间
     * @param {string} dateTimeStr - 日期时间字符串
     * @returns {string} 格式化后的日期时间
     */
    const formatDateTime = (dateTimeStr) => {
      if (!dateTimeStr) return '';
      const date = new Date(dateTimeStr);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    };
    
    /**
     * 加载可用文件列表
     */
    const loadAvailableFiles = async () => {
      try {
        const response = await api.file.getFileList(1, 100);
        if (response.success) {
          availableFiles.value = response.data.files || [];
        }
      } catch (error) {
        ElMessage.error('加载文件列表失败');
        console.error('加载文件列表失败:', error);
      }
    };
    
    /**
     * 加载文件信息
     */
    const loadFileInfo = async () => {
      if (!selectedFileId.value) return;
      
      try {
        // 获取文件预览以获取列信息
        const response = await api.file.previewFile(selectedFileId.value, 1, 50);
        if (response.success) {
          fileInfo.value = {
            ...response.data.file_info,
            row_count: response.data.total_rows,
            column_count: response.data.columns?.length || 0,
            columns: response.data.columns || []
          };
          // 获取详细数据类型
          try {
            const info = await api.file.getFileInfo(selectedFileId.value)
            if (info.success && info.data && info.data.data_types) {
              dataTypes.value = info.data.data_types || {}
            } else {
              dataTypes.value = {}
            }
          } catch (e) {
            dataTypes.value = {}
          }
          
          // 设置默认配置，而不是调用resetConfig()
          const allColumns = fileInfo.value?.columns || [];
          // 计算默认的标准化列（数值列且非标识符）
          const defaultNormalizeCols = allColumns.filter(c => isNumericType(dataTypes.value?.[c]) && !isIdentifierName(c));
          
          preprocessConfig.value = {
            skipHeader: false,
            removeDuplicates: true,
            trimWhitespace: true,
            // 默认使用“均值填补 + Z-Score 标准化”
            missingValueStrategy: 'mean',
            missingValueColumns: [...allColumns], // 默认全选所有列做缺失值处理
            constantValue: '',
            outlierMethod: 'iqr',
            outlierThreshold: 1.5,
            outlierAction: 'clip',
            outlierColumns: [...allColumns], // 当前不会使用
            normalize: true,
            normalizeMethod: 'zscore',
            normalizeColumns: [...defaultNormalizeCols], // 默认选中所有合适的数值列
            decimalPlaces: 7
          };
          
          // 更新全选状态
          isAllOutlierColumnsSelected.value = allColumns.length > 0;
          isAllMissingColumnsSelected.value = allColumns.length > 0;
          isAllNormalizeColumnsSelected.value = defaultNormalizeCols.length > 0;
          
          ElMessage.success('文件信息加载成功');
        }
      } catch (error) {
        ElMessage.error('加载文件信息失败');
        console.error('加载文件信息失败:', error);
      }
    };
    
    /**
     * 异常值处理列全选/取消全选
     * @param {boolean} checked - 是否全选
     */
    const handleOutlierColumnsSelectAll = (checked) => {
      if (checked) {
        // 全选：选择所有特征
        preprocessConfig.value.outlierColumns = [...(fileInfo.value?.columns || [])]
      } else {
        // 取消全选：清空所有选择
        preprocessConfig.value.outlierColumns = []
      }
      // 确保isAllOutlierColumnsSelected状态与实际选择一致
      isAllOutlierColumnsSelected.value = checked
    }
    
    /**
     * 异常值处理列选择变化
     */
    const handleOutlierColumnsSelect = () => {
      // 当异常值处理列选择变化时，重新计算全选状态
      if (!fileInfo.value?.columns || fileInfo.value.columns.length === 0) {
        isAllOutlierColumnsSelected.value = false
        return
      }
      
      const selectedSet = new Set(preprocessConfig.value.outlierColumns)
      
      // 检查是否所有特征都被选中
      isAllOutlierColumnsSelected.value = fileInfo.value.columns.every(col => selectedSet.has(col))
    }
    
    /**
     * 缺失值处理列全选/取消全选
     * @param {boolean} checked - 是否全选
     */
    const handleMissingColumnsSelectAll = (checked) => {
      const visibleCols = filteredMissingColumns.value
      if (!visibleCols || visibleCols.length === 0) {
        isAllMissingColumnsSelected.value = false
        return
      }

      const current = new Set(preprocessConfig.value.missingValueColumns || [])
      if (checked) {
        // 只对当前搜索结果中的列执行全选，其它已选列保持不变
        visibleCols.forEach(c => current.add(c))
      } else {
        // 只对当前搜索结果中的列取消选择，其它列不动
        const visibleSet = new Set(visibleCols)
        for (const c of visibleSet) {
          current.delete(c)
        }
      }
      preprocessConfig.value.missingValueColumns = Array.from(current)

      // 更新“全选”状态：当前过滤列表中的列是否都已选中
      const selectedSet = new Set(preprocessConfig.value.missingValueColumns)
      isAllMissingColumnsSelected.value = visibleCols.every(c => selectedSet.has(c))
    }
    
    /**
     * 缺失值处理列选择变化
     */
    const handleMissingColumnsSelect = () => {
      const visibleCols = filteredMissingColumns.value
      if (!visibleCols || visibleCols.length === 0) {
        isAllMissingColumnsSelected.value = false
        return
      }
      const selectedSet = new Set(preprocessConfig.value.missingValueColumns || [])
      isAllMissingColumnsSelected.value = visibleCols.every(c => selectedSet.has(c))
    }
    
    /**
     * 移除缺失值处理列
     * @param {string} col - 要移除的列名
     */
    const removeMissingColumn = (col) => {
      const index = preprocessConfig.value.missingValueColumns.indexOf(col);
      if (index > -1) {
        preprocessConfig.value.missingValueColumns.splice(index, 1);
      }
      handleMissingColumnsSelect()
    };
    
    /**
     * 移除异常值处理列
     * @param {string} col - 要移除的列名
     */
    const removeOutlierColumn = (col) => {
      const index = preprocessConfig.value.outlierColumns.indexOf(col);
      if (index > -1) {
        preprocessConfig.value.outlierColumns.splice(index, 1);
      }
    };
    
    /**
     * 判断是否是数值类型
     * @param {string} t - 数据类型
     * @returns {boolean} 是否是数值类型
     */
    const isNumericType = (t) => {
      const s = String(t || '').toLowerCase()
      return s.includes('int') || s.includes('float') || s.includes('double') || s.includes('number')
    }

    /**
     * 识别可能的标识符列名
     * @param {string} name - 列名
     * @returns {boolean} 是否是标识符列名
     */
    const isIdentifierName = (name) => {
      const s = String(name || '').toLowerCase()
      return s === 'id' || /(^|[_-])(id)$/.test(s) || /(index|序号|编号)$/.test(s)
    }

    /**
     * 移除标准化列
     * @param {string} col - 要移除的列名
     */
    const removeNormalizeColumn = (col) => {
      const index = preprocessConfig.value.normalizeColumns.indexOf(col);
      if (index > -1) {
        preprocessConfig.value.normalizeColumns.splice(index, 1);
      }
      // 显式刷新“全选”状态，确保与可见/选中列一致
      handleNormalizeColumnsSelect();
    };

    /**
     * 标准化候选列（仅数值列，且排除标识符）
     */
    const normalizeCandidates = computed(() => {
      const cols = fileInfo.value?.columns || []
      return cols.filter(c => isNumericType(dataTypes.value?.[c]) && !isIdentifierName(c))
    })

    /**
     * 缺失值列搜索过滤结果
     */
    const filteredMissingColumns = computed(() => {
      const cols = fileInfo.value?.columns || []
      const kw = (missingColumnSearchKeyword.value || '').trim().toLowerCase()
      if (!kw) return cols
      return cols.filter(name => String(name).toLowerCase().includes(kw))
    })

    /**
     * 标准化列搜索过滤结果
     */
    const filteredNormalizeColumns = computed(() => {
      const cols = normalizeCandidates.value || []
      const kw = (normalizeColumnSearchKeyword.value || '').trim().toLowerCase()
      if (!kw) return cols
      return cols.filter(name => String(name).toLowerCase().includes(kw))
    })

    /**
     * 下方tag展示的缺失值列
     */
    const displayedMissingTags = computed(() => {
      const selectedSet = new Set(preprocessConfig.value.missingValueColumns || [])
      const kw = (missingColumnSearchKeyword.value || '').trim().toLowerCase()
      // 没有关键字时，按照全部列的顺序显示已选列
      if (!kw) {
        const all = fileInfo.value?.columns || []
        return all.filter(col => selectedSet.has(col))
      }
      // 有关键字时，按照当前过滤列表的顺序显示已选列
      const visible = filteredMissingColumns.value || []
      return visible.filter(col => selectedSet.has(col))
    })

    /**
     * 下方tag展示的标准化列
     */
    const displayedNormalizeTags = computed(() => {
      const selectedSet = new Set(preprocessConfig.value.normalizeColumns || [])
      const kw = (normalizeColumnSearchKeyword.value || '').trim().toLowerCase()
      // 没有关键字时，按照候选标准化列的顺序显示已选列
      if (!kw) {
        const all = normalizeCandidates.value || []
        return all.filter(col => selectedSet.has(col))
      }
      // 有关键字时，按照当前过滤列表的顺序显示已选列
      const visible = filteredNormalizeColumns.value || []
      return visible.filter(col => selectedSet.has(col))
    })

    /**
     * 标准化列全选/取消全选
     * @param {boolean} checked - 是否全选
     */
    const handleNormalizeColumnsSelectAll = (checked) => {
      const visibleCols = filteredNormalizeColumns.value
      if (!visibleCols || visibleCols.length === 0) {
        isAllNormalizeColumnsSelected.value = false
        return
      }

      const current = new Set(preprocessConfig.value.normalizeColumns || [])
      if (checked) {
        // 只对当前搜索结果中的列执行全选
        visibleCols.forEach(c => current.add(c))
      } else {
        // 只对当前搜索结果中的列取消选择
        const visibleSet = new Set(visibleCols)
        for (const c of visibleSet) {
          current.delete(c)
        }
      }
      preprocessConfig.value.normalizeColumns = Array.from(current)

      const selectedSet = new Set(preprocessConfig.value.normalizeColumns || [])
      isAllNormalizeColumnsSelected.value = visibleCols.every(c => selectedSet.has(c))
    }

    /**
     * 标准化列选择变化
     */
    const handleNormalizeColumnsSelect = () => {
      const visibleCols = filteredNormalizeColumns.value
      if (!visibleCols || visibleCols.length === 0) {
        isAllNormalizeColumnsSelected.value = false
        return
      }
      const selectedSet = new Set(preprocessConfig.value.normalizeColumns || [])
      isAllNormalizeColumnsSelected.value = visibleCols.every(c => selectedSet.has(c))
    }

    // 监听搜索结果或选中列表变化，自动同步“全选”状态（缺失值列）
    watch(
      [filteredMissingColumns, () => preprocessConfig.value.missingValueColumns],
      ([visible]) => {
        const visibleCols = visible || []
        if (!visibleCols.length) {
          isAllMissingColumnsSelected.value = false
          return
        }
        const selectedSet = new Set(preprocessConfig.value.missingValueColumns || [])
        isAllMissingColumnsSelected.value = visibleCols.every(c => selectedSet.has(c))
      }
    )

    // 监听搜索结果或选中列表变化，自动同步“全选”状态（标准化列）
    watch(
      [filteredNormalizeColumns, () => preprocessConfig.value.normalizeColumns],
      ([visible]) => {
        const visibleCols = visible || []
        if (!visibleCols.length) {
          isAllNormalizeColumnsSelected.value = false
          return
        }
        const selectedSet = new Set(preprocessConfig.value.normalizeColumns || [])
        isAllNormalizeColumnsSelected.value = visibleCols.every(c => selectedSet.has(c))
      }
    )
    
    /**
     * 重置配置
     */
    const resetConfig = () => {
      // 重置为初始状态：清空文件选择、重置配置
      selectedFileId.value = '';
      fileInfo.value = null;
      dataTypes.value = {};
      
      preprocessConfig.value = {
        skipHeader: false,
        removeDuplicates: true,
        trimWhitespace: true,
        // 默认使用“均值填补 + Z-Score 标准化”
        missingValueStrategy: 'mean',
        missingValueColumns: [],
        constantValue: '',
        outlierMethod: 'iqr',
        outlierThreshold: 1.5,
        outlierAction: 'clip',
        outlierColumns: [],
        normalize: true,
        normalizeMethod: 'zscore',
        normalizeColumns: [],
        decimalPlaces: 7
      };
      
      // 重置全选状态
      isAllOutlierColumnsSelected.value = false;
      isAllMissingColumnsSelected.value = false;
      isAllNormalizeColumnsSelected.value = false;
      
      ElMessage.success('预处理配置已重置');
    };
    
    /**
     * 运行预处理
     */
    const runPreprocess = async () => {
      if (!selectedFileId.value) {
        ElMessage.warning('请先选择一个数据文件');
        return;
      }

      const startTime = Date.now();
      const loadingInstance = ElLoading.service({
        lock: true,
        text: '正在进行数据预处理...',
        background: 'rgba(0, 0, 0, 0.7)'
      });

      try {
        const operations = [];

        // 缺失值处理
        const missingCols =
          preprocessConfig.value.missingValueColumns.length > 0
            ? preprocessConfig.value.missingValueColumns
            : fileInfo.value?.columns || [];

        if (preprocessConfig.value.missingValueStrategy === 'skip') {
          operations.push({
            type: 'drop_null',
            parameters: {
              axis: 'rows',
              how: 'any',
              columns: missingCols
            }
          });
        } else if (preprocessConfig.value.missingValueStrategy === 'mean') {
          operations.push({
            type: 'fill_null',
            parameters: {
              method: 'mean',
              columns: missingCols
            }
          });
        } else if (preprocessConfig.value.missingValueStrategy === 'median') {
          operations.push({
            type: 'fill_null',
            parameters: {
              method: 'median',
              columns: missingCols
            }
          });
        } else if (preprocessConfig.value.missingValueStrategy === 'constant') {
          operations.push({
            type: 'fill_null',
            parameters: {
              method: 'constant',
              value: preprocessConfig.value.constantValue,
              columns: missingCols
            }
          });
        }

        // 标准化（仅当用户选择了至少一列时才执行）
        if (
          preprocessConfig.value.normalize &&
          Array.isArray(preprocessConfig.value.normalizeColumns) &&
          preprocessConfig.value.normalizeColumns.length > 0
        ) {
          operations.push({
            type: 'standardize',
            parameters: {
              method: preprocessConfig.value.normalizeMethod,
              columns: preprocessConfig.value.normalizeColumns,
              decimal_places: preprocessConfig.value.decimalPlaces
            }
          });
        }
        
        // 构建请求参数
        const requestParams = {
          file_id: selectedFileId.value,
          operations: operations.map(operation => ({
            ...operation,
            parameters: operation.parameters || operation.params || {}
          }))
        };
        
        // 设置超时控制
        const timeoutPromise = new Promise((_, reject) => {
          setTimeout(() => reject(new Error('请求超时，请检查服务器连接')), 300000); // 5分钟超时
        });
        
        const response = await Promise.race([
          api.preprocess.preprocessData(requestParams),
          timeoutPromise
        ]);
        
        if (response.success) {
          // 添加处理时间
          if (!response.data.processing_time) {
            response.data.processing_time = Date.now() - startTime;
          }

          // 规范化 stats，确保模板可以安全读取字段
          response.data.stats = {
            original_rows: response.data.stats?.original_rows || 0,
            original_columns: response.data.stats?.original_columns || 0,
            processed_rows: response.data.stats?.processed_rows || 0,
            processed_columns: response.data.stats?.processed_columns || 0,
            operations_applied: response.data.stats?.operations_applied || 0,
            duplicates_removed: response.data.stats?.duplicates_removed || 0,
            missing_values_handled: response.data.stats?.missing_values_handled || 0,
            outliers_removed: response.data.stats?.outliers_removed || 0,
            outliers_clipped: response.data.stats?.outliers_clipped || 0,
            features_selected: response.data.stats?.features_selected || 0,
            ...response.data.stats
          };
          
          // 处理返回的数据，确保特殊值显示友好
          if (response.data.sample_data && Array.isArray(response.data.sample_data)) {
            response.data.sample_data = response.data.sample_data.map(row => {
              const formattedRow = { ...row };
              // 处理可能的null、undefined等特殊值
              Object.keys(formattedRow).forEach(key => {
                if (formattedRow[key] === null || formattedRow[key] === undefined) {
                  formattedRow[key] = '-';
                } else if (typeof formattedRow[key] === 'number') {
                  if (isNaN(formattedRow[key])) {
                    formattedRow[key] = 'NaN';
                  } else if (!isFinite(formattedRow[key])) {
                    formattedRow[key] = formattedRow[key] > 0 ? '∞' : '-∞';
                  } else if (Math.abs(formattedRow[key]) > 1e10 || Math.abs(formattedRow[key]) < 1e-6 && formattedRow[key] !== 0) {
                    // 科学计数法显示大数和小数
                    formattedRow[key] = formattedRow[key].toExponential(4);
                  } else {
                    // 常规数字保留适当小数位
                    formattedRow[key] = Number(formattedRow[key].toFixed(4));
                  }
                } else if (typeof formattedRow[key] === 'string' && formattedRow[key].length > 100) {
                  // 截断过长字符串
                  formattedRow[key] = formattedRow[key].substring(0, 100) + '...';
                }
              });
              return formattedRow;
            });
          }
          
          // 扩展统计信息显示
          if (!response.data.statistics) {
            response.data.statistics = {};
          }
          
          preprocessResult.value = response.data;
          resultDialogVisible.value = true;
          
          // 预处理成功后，刷新可用文件列表，并将当前选择切换为处理后的文件
          try {
            await loadAvailableFiles();
            if (response.data.processed_file_id) {
              selectedFileId.value = response.data.processed_file_id;
            }
            // 通知其他页面（如数据管理）刷新文件列表
            try {
              window.dispatchEvent(new Event('files:updated'))
            } catch (_) {}
          } catch (e) {
            // 忽略刷新失败，不影响结果显示
          }
          
          ElMessage.success(`数据预处理成功！处理时间：${(response.data.processing_time / 1000).toFixed(2)}秒`);
        } else {
          throw new Error(response.message || '数据预处理失败');
        }
      } catch (error) {
        // 显示更详细的错误信息
        const errorMessage = error.response?.data?.detail || 
                           error.response?.data?.message || 
                           error.message || 
                           '数据预处理失败，请检查服务器连接或日志';
        ElMessage.error(errorMessage);
        console.error('数据预处理失败:', error);
        
        // 记录详细错误日志
        console.error('错误详情:', {
          message: error.message,
          response: error.response ? { ...error.response } : null,
          stack: error.stack
        });
      } finally {
        // 确保关闭加载状态
        if (loadingInstance && typeof loadingInstance.close === 'function') {
          loadingInstance.close();
        }
      }
    };
    
    /**
     * 关闭结果对话框
     */
    const closeResultDialog = () => {
      resultDialogVisible.value = false;
      preprocessResult.value = null;
    };

    // 组件挂载时加载可用文件
    onMounted(() => {
      loadAvailableFiles();
    });
    
    return {
      selectedFileId,
      availableFiles,
      fileInfo,
      activeCollapseNames,
      preprocessConfig,
      resultDialogVisible,
      preprocessResult,
      isPreprocessing,
      isAllOutlierColumnsSelected,
      isAllMissingColumnsSelected,
      isAllNormalizeColumnsSelected,
      isIdentifierName,
      isNumericType,
      normalizeCandidates,
      // 搜索关键字
      missingColumnSearchKeyword,
      normalizeColumnSearchKeyword,
      // 过滤结果
      filteredMissingColumns,
      filteredNormalizeColumns,
      // 下方 tag 展示用列表
      displayedMissingTags,
      displayedNormalizeTags,
      formatFileSize,
      formatDateTime,
      loadFileInfo,
      removeMissingColumn,
      removeOutlierColumn,
      removeNormalizeColumn,
      resetConfig,
      handleOutlierColumnsSelectAll,
      handleOutlierColumnsSelect,
      handleMissingColumnsSelectAll,
      handleMissingColumnsSelect,
      handleNormalizeColumnsSelectAll,
      handleNormalizeColumnsSelect,
      runPreprocess,
      closeResultDialog
    };
  }
}
</script>

<style scoped>
.preprocess-container {
  padding: 20px;
}

.preprocess-container h1 {
  margin-bottom: 30px;
  color: #303133;
  font-size: 24px;
  font-weight: 600;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #303133;
}

/* 更明确的分隔线与内边距 */
.preprocess-container > :deep(.el-card) {
  padding: 0 !important;
  overflow: hidden;
}

.data-source-selector {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  flex-wrap: nowrap;
}

/* Ensure proper spacing between select and the action button */
.data-source-selector > :deep(.el-select) {
  flex: 1 1 auto;
  min-width: 260px;
  margin-bottom: 0;
}
.data-source-selector > :deep(.el-button) {
  flex: 0 0 auto;
  min-width: 220px;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .data-source-selector {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  .data-source-selector > :deep(.el-select),
  .data-source-selector > :deep(.el-button) {
    width: 100% !important;
    min-width: 0 !important;
  }
}

.option-content {
  display: flex;
  flex-direction: column;
}

.text-gray-500 {
  color: #606266;
  font-size: 12px;
}

.select-all-container {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.feature-list {
  max-height: 220px;
  overflow-y: auto;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-color, #e5e7eb);
  background-color: var(--page-inner-bg);
}

/* 缺失值处理策略和输入框容器 */
.strategy-input-container {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 10px;
}

.selected-features-display {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  max-height: 120px;
  overflow-y: auto;
}

.selection-label {
  color: #606266;
  font-size: 14px;
  font-weight: 500;
}

/* 数据标准化：方法选择 + 小数位数同一行布局 */
.normalize-row {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.normalize-method-select {
  flex: 0 0 260px;
  max-width: 260px;
}

.normalize-method-select :deep(.el-select),
.normalize-method-select :deep(.el-select .el-input) {
  width: 100% !important;
}

.normalize-decimals {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 4px;
}

.decimals-label {
  font-size: 13px;
  color: #606266;
}

.result-header {
  margin-bottom: 20px;
}

.result-header h3 {
  margin-bottom: 8px;
  color: #303133;
}

.result-stats {
  margin-bottom: 20px;
}

/* 数据类型样式差异化 */
.number-cell {
  text-align: right;
  font-family: monospace;
  color: var(--primary-color);
  font-weight: 500;
}

.special-value-cell {
  color: #ff7875;
  font-weight: bold;
  font-style: italic;
}

.missing-value-cell {
  color: #909399;
  font-style: italic;
  opacity: 0.7;
}

.text-cell {
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 对话框样式优化 */
:deep(.el-dialog__body) {
  max-height: 60vh;
  overflow-y: auto;
  padding-bottom: 30px;
}

/* 给预览数据区域加边框，使其作为视觉上的“方框”更加清晰 */
.sample-data {
  border: 1px solid var(--border-strong, rgba(11,43,36,0.18)); /* 使用主题变量的更深 fallback */
  border-radius: calc(var(--radius) + 4px);
  background: var(--surface-color);
  padding: 12px;
  margin-top: 20px;
  width: 100%;
  box-shadow: 0 1px 4px rgba(3,7,18,0.04);
}

.sample-data :deep(.el-table) {
  background: transparent !important; /* 避免表格自身背景覆盖容器 */
}

.sample-data .loading-center {
  padding: 20px 0;
}

/* 表格样式优化 */
:deep(.el-table) {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

:deep(.el-table__header-wrapper th) {
  background-color: var(--page-inner-bg);
  font-weight: 600;
}

:deep(.el-table__body-wrapper) {
  max-height: 400px !important;
}

/* 按钮样式优化 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 响应式优化 */
@media screen and (max-width: 768px) {
  .preprocess-container {
    padding: 10px;
  }
  
  .action-buttons {
    flex-direction: column;
    gap: 10px;
  }
}
</style>

/* 全局样式（非 scoped） - 用于覆盖被 teleport 到 body 的 el-dialog 内容 */
<style>
.el-dialog__body .sample-data {
  /* 更强的边框、outline 和 z-index，确保在任何主题/库样式下都能被看到 */
  border: 2px solid var(--border-strong, rgba(11,43,36,0.22)) !important;
  outline: 1px solid rgba(255,255,255,0.5) !important; /* subtle highlight to separate from background */
  border-radius: calc(var(--radius) + 4px) !important;
  background: var(--surface-color) !important;
  padding: 12px !important;
  margin-top: 20px !important;
  width: 100% !important;
  box-shadow: 0 2px 10px rgba(3,7,18,0.08) !important;
  position: relative !important;
  z-index: 5 !important;
}

.el-dialog__body .sample-data :deep(.el-table) {
  background: transparent !important;
  margin: 0 !important;
}
</style>