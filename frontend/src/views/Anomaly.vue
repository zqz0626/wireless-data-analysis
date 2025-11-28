<template>
  <div class="anomaly-container">
    <h1>异常检测配置</h1>
    
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
          />
        </el-select>
        <el-button type="primary" @click="loadFileInfo()" :disabled="!selectedFileId" class="ds-button">
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

    <!-- 异常检测配置：结构与其他模块的配置卡保持一致 -->
    <el-card shadow="never" v-if="fileInfo">
      <template #header>
        <div class="card-header">
          <span>异常检测配置</span>
        </div>
      </template>

      <el-collapse v-model="activeCollapseNames" class="config-collapse">
        <el-collapse-item title="算法选择" name="basic">
          <div class="config-section">
            <div class="mb-3">
              <el-select v-model="detectionConfig.method" placeholder="选择异常检测算法" style="width: 100%;">
                <el-option label="Isolation Forest" value="isolation_forest" />
              </el-select>
            </div>
          </div>
        </el-collapse-item>
        
        <el-collapse-item title="特征选择" name="features">
          <div class="config-section">
            <div class="select-all-container">
              <el-checkbox
                v-model="isAllSelected"
                @change="handleSelectAll"
                size="small"
                :disabled="isUsingTemplate"
              >
                全选
              </el-checkbox>
              <el-input
                v-model="featureSearchKeyword"
                size="small"
                placeholder="搜索特征"
                clearable
                class="area-search-input"
              />
            </div>
            <div class="feature-list">
              <el-checkbox-group v-model="detectionConfig.targetFeature" @change="handleFeatureSelect" :disabled="isUsingTemplate">
                <template v-for="col in filteredFeatureColumns" :key="col">
                  <el-tooltip :disabled="isNumericType(dataTypes?.[col])" content="非数值列无法参与本算法" placement="top">
                    <el-checkbox
                      :label="col"
                      size="small"
                      class="feature-checkbox"
                      :disabled="isUsingTemplate || !isNumericType(dataTypes?.[col])"
                    >
                      {{ col }}
                    </el-checkbox>
                  </el-tooltip>
                </template>
              </el-checkbox-group>
            </div>
            <div class="selected-features-display" v-if="detectionConfig.targetFeature.length > 0">
              <span class="selection-label">已选择特征：</span>
              <el-tag
                v-for="feature in displayedFeatureTags"
                :key="feature"
                :closable="!isUsingTemplate"
                @close="removeFeature(feature)"
                size="small"
                :title="feature"
                class="feature-tag"
              >
                {{ feature }}
              </el-tag>
            </div>
          </div>
        </el-collapse-item>
        
        <el-collapse-item title="算法参数" name="parameters">
          <div class="config-section" v-if="detectionConfig.method === 'isolation_forest'">
            <div class="params-grid">
              <div class="mb-3">
                <label class="mb-1 block">树的数量</label>
                <el-input-number v-model="detectionConfig.n_estimators" :min="10" :max="1000" :step="10" />
              </div>
              <div class="mb-3">
                <label class="mb-1 block">最大样本量</label>
                <el-select v-model="detectionConfig.max_samples" placeholder="选择样本量">
                  <el-option
                    v-for="opt in maxSampleOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
              </div>
              <div class="mb-3">
                <label class="mb-1 block">预计异常比例</label>
                <div class="slider-row">
                  <div class="slider-label">{{ detectionConfig.contamination.toFixed(3) }}</div>
                  <el-slider
                    v-model="detectionConfig.contamination"
                    :min="0.001"
                    :max="0.1"
                    :step="0.001"
                    :format-tooltip="value => value.toFixed(3)"
                    class="slider-control"
                  />
                </div>
              </div>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- 执行检测：结构与其它模块的执行卡保持一致 -->
    <el-card shadow="never" class="execute-card" v-if="fileInfo">
      <template #header>
        <div class="card-header">
          <span>执行检测</span>
        </div>
      </template>

      <div class="action-buttons">
        <el-button size="large" @click="runDetection" :disabled="!isReady || isDetecting" :loading="isDetecting">
          执行
        </el-button>
        <el-button size="large" @click="saveAsTemplate" :disabled="!canSaveTemplate">
          保存为模板
        </el-button>
        <el-button size="large" @click="resetConfig">
          重置
        </el-button>
      </div>

      <div v-if="taskStatus === 'pending' || taskStatus === 'running'" class="task-progress-bar top">
        <div class="task-progress-text">
          <span>检测任务状态：{{ taskStatus === 'pending' ? '排队中' : '运行中' }}</span>
          <span v-if="taskProgress > 0">（约 {{ Math.round(taskProgress * 100) }}% ）</span>
        </div>
        <el-progress
          :percentage="Math.round((taskProgress || 0) * 100)"
          :stroke-width="8"
          :show-text="false"
        />
      </div>
      
      <div v-if="saveTemplateStatus === 'running'" class="task-progress-bar top">
        <div class="task-progress-text">
          <span>保存模板状态：运行中</span>
          <span v-if="saveTemplateProgress > 0">（约 {{ Math.round(saveTemplateProgress * 100) }}% ）</span>
        </div>
        <el-progress
          :percentage="Math.round((saveTemplateProgress || 0) * 100)"
          :stroke-width="8"
          :show-text="false"
        />
      </div>
    </el-card>

    <!-- 历史模板板块 -->
    <el-card shadow="never" class="template-card">
      <template #header>
        <div class="card-header">
          <span>历史模板</span>
          <el-input 
            v-model="templateSearchKeyword" 
            placeholder="按模板名称搜索" 
            clearable 
            size="small"
            class="template-search-input"
          />
        </div>
      </template>
      <div class="template-content">
        <vxe-table :data="filteredTemplates" style="width: 100%" border stripe fit>
          <vxe-table-column field="results.originalFile.name" title="原文件" min-width="180" resizeable="false">
            <template #default="{ row }">{{ row.results?.originalFile?.name || '未知' }}</template>
          </vxe-table-column>
          <vxe-table-column field="name" title="模板名称" min-width="150" resizeable="false" sortable @sort-change="handleTemplateSort">
            <template #default="{ row }">{{ row.name || row.results?.name || '未知模板' }}</template>
          </vxe-table-column>
          <vxe-table-column field="created_at" title="创建时间" sortable @sort-change="handleTemplateSort" min-width="180" resizeable="false">
            <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
          </vxe-table-column>
          <vxe-table-column field="config.method" title="算法" min-width="120" resizeable="false">
            <template #default="{ row }">{{ row.config.method }}</template>
          </vxe-table-column>
          <vxe-table-column field="config.features" title="特征数量" align="center" min-width="100" resizeable="false">
            <template #default="{ row }">{{ row.config.features.length }}</template>
          </vxe-table-column>
          <vxe-table-column title="操作" align="center" min-width="240" resizeable="false">
            <template #default="{ row }">
              <el-button size="small" @click="loadTemplate(row)">加载</el-button>
              <el-button size="small" type="primary" @click="editTemplateName(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteTemplate(row.id)">删除</el-button>
            </template>
          </vxe-table-column>
        </vxe-table>
      </div>
    </el-card>

    <!-- 异常检测结果：柱形图 + 饼图 + 表格 -->
    <el-card shadow="never" v-if="anomalyResults.length > 0 || taskStatus === 'pending' || taskStatus === 'running'">
      <template #header>
        <div class="card-header">
          <span>异常检测结果</span>
          <div class="scatter-yaxis-selector">
            <el-select
              v-model="selectedYAxisFeature"
              placeholder="选择特征列"
            >
              <el-option
                v-for="col in detectionConfig.targetFeature"
                :key="col"
                :label="col"
                :value="col"
              />
            </el-select>
          </div>
        </div>
      </template>
      <div class="results-content">
        <!-- 严重程度柱形图 + 饼图 -->
        <div class="charts-section-card">
          <div class="charts-two-col">
            <div class="chart-col">
              <div class="chart-title">严重程度分布</div>
              <div class="chart-wrapper" ref="sevWrapper">
                <svg :width="chartWidth" :height="chartHeight">
                  <g>
                    <rect v-for="(item, i) in severityBars" :key="'b-'+item.label"
                      :x="marginLeft + i * (severityBarWidth + 20) + 10"
                      :y="marginTop + (innerHeight - sevHeight(item.count))"
                      :width="severityBarWidth"
                      :height="sevHeight(item.count)"
                      :fill="item.color" rx="8" />
                    <rect v-for="(item, i) in severityBars" :key="'bbg-'+item.label"
                      :x="marginLeft + i * (severityBarWidth + 20) + 10 + severityBarWidth/2 - Math.min(100, severityBarWidth + 24)/2"
                      :y="marginTop + (innerHeight - sevHeight(item.count)) - 22"
                      :width="Math.min(100, severityBarWidth + 24)"
                      :height="18" rx="9"
                      fill="#fff" opacity="0.9" stroke="#e5e7eb" stroke-width="1" />
                    <text v-for="(item, i) in severityBars" :key="'bv-'+item.label"
                      :x="marginLeft + i * (severityBarWidth + 20) + 10 + severityBarWidth/2"
                      :y="marginTop + (innerHeight - sevHeight(item.count)) - 8"
                      text-anchor="middle" fill="#333" font-size="12" font-weight="600">
                      {{ item.count }} ({{ Math.round(item.count / Math.max(1, currentYAxisTotal) * 100) }}%)
                    </text>
                    <line :x1="marginLeft" :y1="marginTop + innerHeight + 0.5" :x2="chartWidth - marginRight" :y2="marginTop + innerHeight + 0.5" stroke="#d0d0d0" stroke-width="1.2" />
                    <line :x1="marginLeft + 0.5" :y1="marginTop" :x2="marginLeft + 0.5" :y2="marginTop + innerHeight" stroke="#e6e6e6" />
                    <text v-for="(item, i) in severityBars" :key="'xl-'+item.label"
                      :x="marginLeft + i * (severityBarWidth + 20) + 10 + severityBarWidth/2"
                      :y="marginTop + innerHeight + 16" text-anchor="middle" class="chart-axis-text">{{ item.label }}</text>
                    <line v-for="t in [0.25,0.5,0.75]" :key="'yg-'+t" :x1="marginLeft" :y1="yGrid(t)" :x2="chartWidth - marginRight" :y2="yGrid(t)" stroke="#f0f0f0" />
                    <text v-for="t in histYTicks" :key="'yl-'+t" :x="marginLeft - 8" :y="yGrid(t)+4" text-anchor="end" class="chart-axis-text">{{ Math.round(t * maxSevCount) }}</text>
                    <!-- Y-axis title -->
                    <text :x="12" :y="marginTop + innerHeight/2" text-anchor="middle" transform="rotate(-90 12 190)" class="chart-axis-title" font-size="13" font-weight="600" fill="#606266">数量</text>
                    <!-- X-axis title -->
                    <text :x="(marginLeft + chartWidth - marginRight)/2" :y="marginTop + innerHeight + 38" text-anchor="middle" class="chart-axis-title" font-size="13" font-weight="600" fill="#606266">严重程度</text>
                  </g>
                </svg>
              </div>
            </div>
            <div class="chart-col">
              <div class="chart-title">严重程度占比</div>
              <div class="pie-chart-container">
                <div class="chart-wrapper pie-svg-wrapper" ref="pieWrapper">
                  <svg width="280" height="280" viewBox="0 0 280 280">
                    <g>
                      <path v-for="seg in severityPieArcs" :key="'arc-'+seg.key" :d="seg.d" :fill="seg.color" opacity="0.95" />
                    </g>
                  </svg>
                </div>
                <div class="pie-legend-vertical">
                  <div class="legend-item" v-for="seg in severityPieLegend" :key="'leg-'+seg.key">
                    <span class="legend-dot" :style="{background: seg.color}"></span>
                    <div class="legend-text">
                      <div class="legend-label">{{ seg.label }}</div>
                      <div class="legend-value">{{ Math.round(seg.percent*100) }}% ({{ Math.round(seg.percent * Math.max(1, currentYAxisTotal)) }})</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </el-card>

    <!-- 散点图显示：原始散点 + 改正后散点 -->
    <el-card shadow="never" v-if="anomalyResults.length > 0 || taskStatus === 'finished'">
      <template #header>
        <div class="card-header">
          <span>散点图显示</span>
        </div>
      </template>
      <div class="results-content">
        <div class="charts-section-card">
          <div class="charts-two-col">
            <!-- 原始散点图 -->
            <div class="chart-col scatter-col">
              <div class="chart-header scatter-header">
                <div class="chart-title">原始散点图（红色为异常点）</div>
                <div class="scatter-legend-buttons">
                  <el-button
                    size="small"
                    :type="showNormalPoints ? 'primary' : 'default'"
                    @click="showNormalPoints = !showNormalPoints"
                  >
                    显示正常点
                  </el-button>
                  <el-button
                    size="small"
                    :type="showAnomalyPoints ? 'primary' : 'default'"
                    @click="showAnomalyPoints = !showAnomalyPoints"
                  >
                    显示异常点
                  </el-button>
                </div>
              </div>
              <div class="chart-wrapper scatter-wrapper" ref="scatterWrapper">
                <div class="scatter-svg-container">
                  <div
                    ref="scatterChartRef"
                    class="scatter-echart"
                  ></div>
                  <div v-if="!scatterHasData" class="chart-placeholder">暂无可用散点数据</div>
                </div>
              </div>
            </div>

            <!-- 改正后散点图 -->
            <div class="chart-col scatter-col">
              <div class="chart-header scatter-header">
                <div class="chart-title">改正后散点图（插值结果）</div>
                <div class="scatter-legend-buttons">
                  <el-button
                    size="small"
                    :type="showCorrectedTrack ? 'primary' : 'default'"
                    @click="showCorrectedTrack = !showCorrectedTrack"
                  >
                    显示改正后轨迹
                  </el-button>
                  <el-button
                    size="small"
                    :type="showCorrectedAnomaly ? 'primary' : 'default'"
                    @click="showCorrectedAnomaly = !showCorrectedAnomaly"
                  >
                    显示改正后异常点
                  </el-button>
                </div>
              </div>
              <div class="chart-wrapper scatter-wrapper" ref="correctedScatterWrapper">
                <div class="scatter-svg-container">
                  <div
                    ref="correctedScatterChartRef"
                    class="scatter-echart"
                  ></div>
                  <div v-if="!scatterHasCorrectedData" class="chart-placeholder">暂无改正后散点数据</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 底部模块：异常检测结果与插值后结果 -->
    <el-card shadow="never" v-if="anomalyResults.length > 0">
      <template #header>
        <div class="card-header">
          <span>异常检测结果与插值后结果</span>
        </div>
      </template>
      <div class="results-content compare-section" ref="compareTableWrapper">
        <div class="chart-header">
          <div class="header-left">
            <el-input
              v-model="compareSearchTextInput"
              size="small"
              placeholder="按数据行索引搜索"
              clearable
              class="index-search-input"
            />
          </div>
          <div class="header-right">
            <el-checkbox-group
              v-model="selectedCompareSeverities"
              size="small"
              class="sev-group"
            >
              <el-checkbox-button label="低" />
              <el-checkbox-button label="中" />
              <el-checkbox-button label="高" />
            </el-checkbox-group>
          </div>
        </div>

        <el-table
          :data="pagedCompareRows"
          style="width: 100%"
          max-height="420"
          @sort-change="handleCompareSortChange"
        >
          <el-table-column prop="timestamp" label="时间戳" width="180">
            <template #default="scope">
              {{ scope.row.timestamp }}
            </template>
          </el-table-column>
          <el-table-column prop="row_index" label="数据行索引" sortable="custom" />
          <el-table-column prop="score" label="异常分数" sortable="custom">
            <template #default="scope">
              <div class="score-display">
                <div class="score-value">{{ typeof scope.row.score === 'number' ? scope.row.score.toFixed(3) : scope.row.score }}</div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="originalValue" label="原数据">
            <template #default="scope">
              {{ typeof scope.row.originalValue === 'number' ? scope.row.originalValue.toFixed(7) : scope.row.originalValue }}
            </template>
          </el-table-column>
          <el-table-column prop="correctedValue" label="插值后结果">
            <template #default="scope">
              {{ typeof scope.row.correctedValue === 'number' ? scope.row.correctedValue.toFixed(7) : scope.row.correctedValue }}
            </template>
          </el-table-column>
          <el-table-column prop="severity" label="严重程度" width="90">
            <template #default="scope">
              <el-tag :type="getSeverityType(scope.row.severity)" size="small">
                {{ scope.row.severity }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>

        <div class="compare-pagination">
          <el-pagination
            background
            layout="sizes, prev, pager, next, jumper"
            :current-page="compareCurrentPage"
            :page-size="comparePageSize"
            :page-sizes="comparePageSizes"
            :total="sortedCompareRows.length"
            @current-change="(p) => compareCurrentPage = p"
            @size-change="(s) => handleComparePageSizeChange(s)"
          />
        </div>
      </div>
    </el-card>

    <!-- 特征值详情对话框 -->
    <el-dialog
      v-model="featureDetailsVisible"
      title="异常样本特征详情"
      width="600px"
    >
      <div v-if="selectedAnomaly" class="feature-details">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="样本ID">{{ selectedAnomaly.id }}</el-descriptions-item>
          <el-descriptions-item label="数据行索引">{{ selectedAnomaly.row_index }}</el-descriptions-item>
          <el-descriptions-item label="异常分数">{{ selectedAnomaly.score.toFixed(4) }}</el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <el-tag :type="getSeverityType(selectedAnomaly.severity)" size="small">
              {{ selectedAnomaly.severity }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div class="mt-4">
          <h4>特征值</h4>
          <el-table :data="getFeatureTableData(selectedAnomaly)" style="width: 100%" border>
            <el-table-column prop="feature" label="特征名称" />
            <el-table-column prop="value" label="特征值">
              <template #default="scope">
                {{ typeof scope.row.value === 'number' ? scope.row.value.toFixed(4) : scope.row.value }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="featureDetailsVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>

  </div>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import api from '../api/index'
const { template: templateApi } = api

/**
 * 异常检测组件
 * 用于配置和执行异常检测任务，展示检测结果和可视化图表
 * 包含数据源选择、算法配置、结果展示等功能
 */
export default {
  name: 'AnomalyDetection',
  components: {},
  setup() {
    // 响应式数据
    const selectedFileId = ref('')
    const availableFiles = ref([])
    const fileInfo = ref(null)
    const anomalyResults = ref([])
    const scatterData = ref(null) // 当前显示的散点图数据
    const allScatterData = ref({}) // 所有特征列的散点图数据，key为特征名，value为散点图数据
    const scatterWrapper = ref(null)
    const scatterChartRef = ref(null)
    const correctedScatterWrapper = ref(null)
    const correctedScatterChartRef = ref(null)
    const compareTableWrapper = ref(null)
    const selectedYAxisFeature = ref('')
    const detectionTime = ref(0)
    // 异常检测任务相关
    const taskId = ref('')
    const taskStatus = ref('idle') // idle | pending | running | finished | failed
    const taskProgress = ref(0)
    let taskPollTimer = null
    // 保存模板相关
    const saveTemplateStatus = ref('idle') // idle | pending | running | finished | failed
    const saveTemplateProgress = ref(0)
    // 记录最近一次检测生成的修正文件路径和异常行索引，供切换 Y 轴时重绘使用
    const lastCorrectedFilePath = ref('')
    const lastAnomalyIndices = ref([])
    const featureAnomaliesMap = ref({})
    const featureDetailsVisible = ref(false)
    const selectedAnomaly = ref(null)
    // 检测配置面板：默认全部收起
    const activeCollapseNames = ref([])
    
    // 历史模板数据
    const historyTemplates = ref([])
    // 模板搜索关键字
    const templateSearchKeyword = ref('')
    // 模板排序配置
    const templateSort = ref({
      prop: 'createdAt',
      order: 'descending' // 默认按创建时间倒序
    })
    
    // 配置对象

    const detectionConfig = ref({
      method: 'isolation_forest',
      contamination: 0.018,
      n_estimators: 100,
      max_samples: 'auto',
      n_neighbors: 20,
      algorithm: 'auto',
      kernel: 'rbf',
      nu: 0.5,
      targetFeature: []
    })

    // 散点图开关与悬停状态
    const showNormalPoints = ref(true)
    const showAnomalyPoints = ref(true)
    const showCorrectedTrack = ref(true)
    const showCorrectedAnomaly = ref(true)
    const hoverPoint = ref(null)
    
    // 文件列类型
    const dataTypes = ref({})

    // 计算属性
    const isAllSelected = ref(false)
    const featureSearchKeyword = ref('')
    
    const isNumericType = (t) => {
      const s = String(t || '').toLowerCase()
      return s.includes('int') || s.includes('float') || s.includes('double') || s.includes('number')
    }

    const numericColumns = computed(() => {
      const types = dataTypes.value || {}
      const cols = Object.keys(types)
      if (cols.length) {
        return cols.filter(c => isNumericType(types[c]))
      }
      // 回退：没有类型信息时，退回所有列
      return fileInfo.value?.columns || []
    })

    const filteredFeatureColumns = computed(() => {
      let cols = numericColumns.value || []
      
      // 如果正在使用模板，只显示已选择的特征
      if (isUsingTemplate.value) {
        const selected = detectionConfig.value.targetFeature || []
        cols = cols.filter(col => selected.includes(col))
      }
      
      const kw = (featureSearchKeyword.value || '').trim().toLowerCase()
      if (!kw) return cols
      return cols.filter(name => String(name).toLowerCase().includes(kw))
    })
    
    const isDetecting = computed(() => taskStatus.value === 'pending' || taskStatus.value === 'running')

    const isReady = computed(() => {
      return selectedFileId.value && fileInfo.value && detectionConfig.value.targetFeature.length > 0
    })
    
    // 是否可以保存模板（需要先执行检测，获取结果）
    const canSaveTemplate = computed(() => {
      return isReady.value && anomalyResults.value.length > 0
    })
    const maxSampleOptions = computed(() => {
      const n = fileInfo.value?.row_count || 0
      const base = [256, 512, 1024, 2048]
      const opts = [{ label: '自动 (auto)', value: 'auto' }]
      for (const v of base) {
        if (!n || v <= n) opts.push({ label: String(v), value: v })
      }
      return opts
    })
    
    // 按当前 Y 轴特征筛选的异常列表：仅保留由该特征触发的异常
    const yAxisAnomalies = computed(() => {
      const all = anomalyResults.value || []
      const y = selectedYAxisFeature.value
      if (!y) return []

      const map = featureAnomaliesMap.value || {}
      const indicesFromMap = Array.isArray(map[y]) ? map[y] : []
      if (indicesFromMap.length) {
        const set = new Set(indicesFromMap.map(n => Number(n)))
        return all.filter(a => set.has(Number(a.row_index)))
      }

      // 回退：使用 trigger_features 来筛选
      return all.filter(a => {
        const triggers = a.trigger_features || []
        if (!Array.isArray(triggers) || triggers.length === 0) return false
        return triggers.includes(y)
      })
    })
    
    // 过滤和排序后的模板列表
    const filteredTemplates = computed(() => {
      let templates = [...historyTemplates.value]
      
      // 按名称搜索
      if (templateSearchKeyword.value) {
        const keyword = templateSearchKeyword.value.trim().toLowerCase()
        templates = templates.filter(template => {
          const templateName = (template.name || template.results?.name || '').toLowerCase()
          return templateName.includes(keyword)
        })
      }
      
      // 排序
      if (templateSort.value.prop && templateSort.value.order) {
        const { prop, order } = templateSort.value
        templates.sort((a, b) => {
          let aVal, bVal
          
          // 处理创建时间排序
          if (prop === 'created_at') {
            aVal = new Date(a.created_at)
            bVal = new Date(b.created_at)
            // 处理无效日期
            if (isNaN(aVal.getTime()) && isNaN(bVal.getTime())) return 0
            if (isNaN(aVal.getTime())) return order === 'ascending' ? 1 : -1
            if (isNaN(bVal.getTime())) return order === 'ascending' ? -1 : 1
            return order === 'ascending' ? aVal - bVal : bVal - aVal
          } 
          // 处理模板名称排序，特殊处理name字段可能存在于不同位置的情况
          else if (prop === 'name') {
            aVal = a.name || a.results?.name || ''
            bVal = b.name || b.results?.name || ''
          }
          // 处理嵌套属性排序
          else if (prop.includes('.')) {
            const [parent, child] = prop.split('.')
            aVal = a[parent]?.[child]
            bVal = b[parent]?.[child]
          }
          // 处理普通属性排序
          else {
            aVal = a[prop]
            bVal = b[prop]
          }
          
          if (typeof aVal === 'string' && typeof bVal === 'string') {
            // 按字符串排序
            return order === 'ascending' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
          } else if (typeof aVal === 'number' && typeof bVal === 'number') {
            // 按数字排序
            return order === 'ascending' ? aVal - bVal : bVal - aVal
          }
          return 0
        })
      }
      
      return templates
    })

    // 对比表格分页，避免一次性渲染过多行导致卡顿
    const compareCurrentPage = ref(1)
    const comparePageSize = ref(200)
    const comparePageSizes = ref([50, 100, 200, 500])

    const pagedCompareRows = computed(() => {
      const total = sortedCompareRows.value.length
      if (!total) return []
      const size = comparePageSize.value
      const lastPage = Math.max(1, Math.ceil(total / size))
      const page = Math.min(compareCurrentPage.value, lastPage)
      const start = (page - 1) * size
      const end = start + size
      return sortedCompareRows.value.slice(start, end)
    })

    // 底部对比表格数据：行索引 + 时间戳 + 分数 + 原始值 + 插值后结果 + 严重程度
    const detailedCompareRows = computed(() => {
      // 确保响应selectedYAxisFeature的变化
      const currentFeature = selectedYAxisFeature.value || detectionConfig.value.targetFeature[0]
      
      // 获取当前特征的scatterData
      let s = scatterData.value
      if (!s || s.y_label !== currentFeature) {
        // 如果当前scatterData不是当前特征的数据，从allScatterData中获取
        s = allScatterData.value[currentFeature] || null
      }
      
      // 直接使用yAxisAnomalies计算属性，它已经根据当前Y轴特征过滤了异常结果
      const filteredAnomalies = yAxisAnomalies.value
      
      // 如果还是没有scatterData，尝试从过滤后的异常结果中直接获取数据
      if (!s) {
        return filteredAnomalies.map(r => ({
          row_index: Number(r.row_index),
          score: r.score,
          severity: r.severity,
          timestamp: r.timestamp,
          originalValue: r.feature_values ? r.feature_values[currentFeature] : null,
          correctedValue: null, // 无法获取修正后的值
          raw: r
        }))
      }

      const buildMap = (arr) => {
        const map = new Map()
        ;(arr || []).forEach(p => {
          if (p && p.row_index != null && p.value != null) {
            map.set(Number(p.row_index), p)
          }
        })
        return map
      }

      const originalMap = buildMap((s.normal_points || []).concat(s.anomaly_points || []))
      const correctedMap = buildMap((s.corrected_points || []).concat(s.corrected_anomaly_points || []))

      return filteredAnomalies.map(r => {
        const idx = Number(r.row_index)
        const orig = originalMap.get(idx)
        const corr = correctedMap.get(idx)
        return {
          row_index: idx,
          score: r.score,
          severity: r.severity,
          timestamp: r.timestamp,
          originalValue: orig ? orig.value : (r.feature_values ? r.feature_values[currentFeature] : null),
          correctedValue: corr ? corr.value : null,
          raw: r
        }
      })
    })

    const selectedCompareSeverities = ref(['低', '中', '高'])
    const compareSearchTextInput = ref('')
    const compareSearchText = ref('')
    const compareSortProp = ref('')
    const compareSortOrder = ref('')

    // 右上角对比表索引搜索增加轻量防抖，避免每个按键都重新过滤大表
    let compareSearchTimer = null
    watch(compareSearchTextInput, (val) => {
      if (compareSearchTimer) clearTimeout(compareSearchTimer)
      compareSearchTimer = setTimeout(() => {
        compareSearchText.value = val
        compareCurrentPage.value = 1
      }, 200)
    })

    // 严重程度筛选变化时回到第一页，避免落在空页
    watch(selectedCompareSeverities, () => {
      compareCurrentPage.value = 1
    })

    const filteredCompareRows = computed(() => {
      const sevArr = selectedCompareSeverities.value || []
      const sevSet = new Set(sevArr)
      const kw = (compareSearchText.value || '').trim()
      const hasKw = kw !== ''

      return detailedCompareRows.value.filter(r => {
        // 如果一个都没选，则不展示任何行（而不是全部展示）
        if (sevSet.size === 0) return false
        const sevOk = sevSet.has(r.severity)
        const indexStr = String(r.row_index ?? '')
        const indexOk = !hasKw || indexStr.includes(kw)
        return sevOk && indexOk
      })
    })

    const sortedCompareRows = computed(() => {
      const base = filteredCompareRows.value.slice()
      if (!compareSortProp.value || !compareSortOrder.value) return base

      const factor = compareSortOrder.value === 'ascending' ? 1 : -1
      return base.sort((a, b) => {
        let va = a[compareSortProp.value]
        let vb = b[compareSortProp.value]
        if (compareSortProp.value === 'timestamp') {
          // 时间戳按原始字符串比较即可（不做取舍）
          va = String(va || '')
          vb = String(vb || '')
        }
        if (va === vb) return 0
        return va > vb ? factor : -factor
      })
    })


    // 删除特征的方法
    const removeFeature = (feature) => {
      const index = detectionConfig.value.targetFeature.indexOf(feature)
      if (index > -1) {
        detectionConfig.value.targetFeature.splice(index, 1)
      }
      // 更新全选状态
      handleFeatureSelect()
    }

    const displayedFeatureTags = computed(() => {
      const selectedSet = new Set(detectionConfig.value.targetFeature || [])
      const kw = (featureSearchKeyword.value || '').trim().toLowerCase()
      if (!kw) {
        const all = numericColumns.value || []
        return all.filter(col => selectedSet.has(col))
      }
      const visible = filteredFeatureColumns.value || []
      return visible.filter(col => selectedSet.has(col))
    })

    // 方法
    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }
    
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
    
    const handleCompareSortChange = ({ prop, order }) => {
      compareSortProp.value = prop || ''
      compareSortOrder.value = order || ''
    }

    const handleComparePageSizeChange = (size) => {
      comparePageSize.value = size
      compareCurrentPage.value = 1
    }

    const loadAvailableFiles = async () => {
      try {
        const response = await api.file.getFileList(1, 100)
        if (response.success) {
          availableFiles.value = response.data.files || []
        }
      } catch (error) {
        ElMessage.error('加载文件列表失败')
        console.error('加载文件列表失败:', error)
      }
    }
    
    const loadFileInfo = async (fileId) => {
      // 如果提供了fileId参数，使用该参数，否则使用selectedFileId.value
      let id = fileId || selectedFileId.value
      // 确保id是字符串类型，避免API请求错误
      id = String(id)
      if (!id) return
      
      try {
        // 获取文件预览以获取列信息
        const response = await api.file.previewFile(id, 1, 1)
        if (response.success) {
          fileInfo.value = {
            ...response.data.file_info,
            row_count: response.data.total_rows,
            column_count: response.data.columns?.length || 0,
            columns: response.data.columns || []
          }
          // 获取详细数据类型以筛选数值列
          try {
            const info = await api.file.getFileInfo(id)
            if (info.success && info.data && info.data.data_types) {
              dataTypes.value = info.data.data_types
            } else {
              dataTypes.value = {}
            }
          } catch (e) {
            dataTypes.value = {}
          }
          // 只有在非模板使用状态下才重置特征选择
          if (!isUsingTemplate.value) {
            detectionConfig.value.targetFeature = []
            isAllSelected.value = false
            activeCollapseNames.value = []
          }
          ElMessage.success('文件信息加载成功')
        } else {
          ElMessage.error('获取文件预览失败')
          return
        }
      } catch (error) {
        console.error('加载文件信息失败:', error)
        // 检查是否是文件不存在的错误
        if (error.error === 'HTTP_404' || error.message.includes('不存在') || error.message.includes('404')) {
          ElMessage.error('原文件已被删除，无法加载')
        } else {
          ElMessage.error('加载文件信息失败')
        }
        // 加载失败时，保持模板中保存的文件信息
        // 不重置任何状态
      }
    }
    
    const handleSelectAll = (checked) => {
      // 使用模板时禁用全选功能
      if (isUsingTemplate.value) return
      
      const visible = filteredFeatureColumns.value
      if (!visible || visible.length === 0) {
        isAllSelected.value = false
        return
      }

      const current = new Set(detectionConfig.value.targetFeature || [])
      if (checked) {
        // 只对当前搜索结果中的数值特征执行全选
        visible.forEach(c => current.add(c))
      } else {
        // 只对当前搜索结果中的特征取消选择
        const visibleSet = new Set(visible)
        for (const c of visibleSet) {
          current.delete(c)
        }
      }
      detectionConfig.value.targetFeature = Array.from(current)

      const selectedSet = new Set(detectionConfig.value.targetFeature || [])
      isAllSelected.value = visible.every(c => selectedSet.has(c))
    }
    
    const handleFeatureSelect = () => {
      const visible = filteredFeatureColumns.value
      if (!visible || visible.length === 0) {
        isAllSelected.value = false
        return
      }
      const selectedSet = new Set(detectionConfig.value.targetFeature || [])
      isAllSelected.value = visible.every(col => selectedSet.has(col))
    }

    const updateSelectAllStatus = () => {
      const visible = filteredFeatureColumns.value
      if (!visible || visible.length === 0) {
        isAllSelected.value = false
        return
      }
      const selectedSet = new Set(detectionConfig.value.targetFeature || [])
      isAllSelected.value = visible.every(col => selectedSet.has(col))
    }
    
    const resetConfig = () => {
      // 重置模板使用状态
      isUsingTemplate.value = false
      
      // 重置为初始状态：清空文件选择、重置配置、清空结果
      selectedFileId.value = ''
      fileInfo.value = null
      detectionConfig.value = {
        method: 'isolation_forest',
        contamination: 0.018,
        n_estimators: 100,
        max_samples: 'auto',
        n_neighbors: 20,
        algorithm: 'auto',
        kernel: 'rbf',
        nu: 0.5,
        targetFeature: []
      }
      
      // 重置全选状态和结果
      isAllSelected.value = false
      anomalyResults.value = []
      detectionTime.value = 0
      scatterData.value = null
      selectedYAxisFeature.value = ''
      // 重置任务状态，确保散点图模块不显示
      taskStatus.value = 'idle'
      
      ElMessage.success('异常检测配置已重置')
    }
    
    const clearTaskTimer = () => {
      if (taskPollTimer) {
        clearInterval(taskPollTimer)
        taskPollTimer = null
      }
    }

    const runDetection = async () => {
      if (!isReady.value) {
        ElMessage.warning('请先选择文件和特征')
        return
      }
      // 运行前强制仅使用数值列
      let filtered = (detectionConfig.value.targetFeature || []).filter(f => isNumericType(dataTypes.value?.[f]))
      if (filtered.length !== detectionConfig.value.targetFeature.length) {
        ElMessage.warning('已自动移除非数值列，仅对数值列进行异常检测')
        detectionConfig.value.targetFeature = filtered
      }
      if (detectionConfig.value.targetFeature.length === 0) {
        ElMessage.error('所选特征均为非数值列，无法进行异常检测')
        return
      }
      try {
        // 开始计时
        const startTime = performance.now()

        // 构建请求参数
        const params = {
          file_id: selectedFileId.value,
          method: detectionConfig.value.method,
          contamination: detectionConfig.value.contamination,
          features: detectionConfig.value.targetFeature,
          y_axis_feature: selectedYAxisFeature.value || detectionConfig.value.targetFeature[0]
        }

        // 根据不同方法添加特定参数
        if (detectionConfig.value.method === 'isolation_forest') {
          params.n_estimators = detectionConfig.value.n_estimators
          params.max_samples = detectionConfig.value.max_samples
        }

        // 提交异常检测任务
        const response = await api.analysis.submitAnomalyTask(params)

        if (!response.success || !response.data || !response.data.task_id) {
          throw new Error(response.message || '任务提交失败')
        }

        taskId.value = response.data.task_id
        taskStatus.value = 'pending'
        taskProgress.value = 0

        clearTaskTimer()

        const pollTaskStatus = async () => {
          if (!taskId.value) return
          try {
            const statusResp = await api.analysis.getAnomalyTaskStatus(taskId.value)
            if (!statusResp.success || !statusResp.data) return

            const data = statusResp.data
            taskStatus.value = data.status
            taskProgress.value = Number(data.progress || 0)

            if (data.status === 'finished') {
              clearTaskTimer()
              const result = data.result
              if (!result) {
                throw new Error('任务结果为空')
              }

              const anomalies = result.anomalies || []
              anomalyResults.value = anomalies.map(anomaly => ({
                id: anomaly.id,
                row_index: anomaly.row_index,
                severity: anomaly.severity,
                score: anomaly.score,
                timestamp: anomaly.timestamp,
                description: anomaly.description,
                feature_values: anomaly.feature_values,
                trigger_features: anomaly.trigger_features || []
              }))

              // 记录异常行索引与修正后文件路径，供后续切换 Y 轴重绘使用
              lastAnomalyIndices.value = anomalies.map(a => a.row_index)
              lastCorrectedFilePath.value = result.corrected_file && result.corrected_file.path ? result.corrected_file.path : ''
              featureAnomaliesMap.value = result.feature_anomalies || {}

              // 清空当前选择与散点图，等待用户重新选择 Y 轴
              scatterData.value = null
              selectedYAxisFeature.value = ''

              // 为所有特征列生成散点图数据
              const generateAllScatterData = async () => {
                const features = detectionConfig.value.targetFeature
                for (const feature of features) {
                  try {
                    let indices = []
                    const map = featureAnomaliesMap.value || {}
                    if (Array.isArray(map[feature]) && map[feature].length) {
                      indices = map[feature].map(n => Number(n))
                    } else {
                      indices = (anomalyResults.value || [])
                        .filter(a => {
                          const triggers = a.trigger_features || []
                          if (!Array.isArray(triggers) || triggers.length === 0) return false
                          return triggers.includes(feature)
                        })
                        .map(a => a.row_index)
                    }

                    const resp = await api.analysis.regenerateScatter({
                      base_file_id: fileInfo.value.id,
                      corrected_file_path: lastCorrectedFilePath.value,
                      y_axis_feature: feature,
                      anomaly_indices: indices,
                    })

                    if (resp && resp.success && resp.data) {
                      allScatterData.value[feature] = resp.data
                    }
                  } catch (err) {
                    console.error(`生成特征 ${feature} 的散点图数据失败:`, err)
                  }
                }
              }

              // 生成所有特征列的散点图数据
              await generateAllScatterData()

              // 初始化选中的Y轴特征
              if (detectionConfig.value.targetFeature.length > 0) {
                selectedYAxisFeature.value = detectionConfig.value.targetFeature[0]
              }

              // 结束计时
              detectionTime.value = Math.round(performance.now() - startTime)

              ElMessage.success(`异常检测完成，发现 ${result.anomaly_count} 个异常样本`)
            } else if (data.status === 'failed') {
              clearTaskTimer()
              taskStatus.value = 'failed'
              ElMessage.error('异常检测失败: ' + (data.error || '未知错误'))
              anomalyResults.value = []
              detectionTime.value = 0
              scatterData.value = null
            } else {
              // pending / running: 继续轮询
            }
          } catch (err) {
            clearTaskTimer()
            ElMessage.error('查询异常检测任务状态失败: ' + (err.message || '未知错误'))
            console.error('查询异常任务状态失败:', err)
          }
        }

        // 立即查询一次，然后每 2 秒轮询
        await pollTaskStatus()
        taskPollTimer = setInterval(pollTaskStatus, 2000)
      } catch (error) {
        clearTaskTimer()
        ElMessage.error('异常检测失败: ' + (error.message || '未知错误'))
        console.error('异常检测失败:', error)

        anomalyResults.value = []
        detectionTime.value = 0
        scatterData.value = null
        lastAnomalyIndices.value = []
        lastCorrectedFilePath.value = ''
        featureAnomaliesMap.value = {}
      }
    }

    const getMethodName = () => {
      const methodMap = {
        'isolation_forest': 'Isolation Forest'
      }
      return methodMap[detectionConfig.value.method] || detectionConfig.value.method
    }

    // 添加一个标志位，防止generateScatterDataForFeature函数被频繁调用
    let isGeneratingScatter = false
    
    // 切换 Y 轴时，从allScatterData中获取数据，如果没有则自动生成
    watch(selectedYAxisFeature, async (newFeature) => {
      if (!newFeature) return
      
      // 如果allScatterData中有该特征的数据，直接使用
      if (allScatterData.value[newFeature]) {
        scatterData.value = allScatterData.value[newFeature]
        return
      }
      
      // 如果有模板加载的scatterData且y_label匹配，直接使用
      if (scatterData.value && scatterData.value.y_label === newFeature) {
        return
      }
      
      // 如果有文件信息，自动生成该特征的散点图数据
      if (fileInfo.value && !isGeneratingScatter) {
        try {
          isGeneratingScatter = true
          await generateScatterDataForFeature(newFeature)
        } finally {
          isGeneratingScatter = false
        }
      } else {
        console.log(`特征 ${newFeature} 的散点图数据不存在，且没有文件信息或正在生成中`)
      }
    })

    const getAnomalyPercentage = () => {
      if (!fileInfo.value || fileInfo.value.row_count === 0) return 0
      return ((anomalyResults.value.length / fileInfo.value.row_count) * 100).toFixed(2)
    }

    const getSeverityType = (severity) => {
      const typeMap = {
        '低': 'primary',
        '中': 'warning',
        '高': 'danger'
      }
      return typeMap[severity] || 'info'
    }
    
    const getProgressColor = (score) => {
      if (score < 0.3) return '#67C23A'
      if (score < 0.7) return '#E6A23C'
      return '#F56C6C'
    }
    
    const truncateText = (text, maxLength) => {
      if (!text || text.length <= maxLength) return text
      return text.substring(0, maxLength) + '...'
    }

    const prettyAxisLabel = (value) => {
      if (value === null || value === undefined) return ''
      const str = String(value)
      const d = new Date(str)
      if (!isNaN(d.getTime())) {
        return d.toLocaleString('zh-CN', {
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        })
      }
      return str.length > 16 ? str.slice(0, 16) : str
    }

    const showFeatureDetails = (anomaly) => {
      selectedAnomaly.value = anomaly
      featureDetailsVisible.value = true
    }

    const getFeatureTableData = (anomaly) => {
      if (!anomaly || !anomaly.feature_values) return []

      return Object.entries(anomaly.feature_values).map(([feature, value]) => ({
        feature,
        value
      }))
    }

    const chartWidth = ref(600) // bar chart width
    const chartWidthPie = ref(600) // pie chart width
    const chartWidthScatter = ref(600)
    const chartHeight = 420
    // margins for visible axes
    const marginTop = 40
    const marginRight = 20
    const marginBottom = 50
    const marginLeft = 50
    const innerWidth = computed(() => chartWidth.value - marginLeft - marginRight)
    const innerWidthScatter = computed(() => chartWidthScatter.value - marginLeft - marginRight)
    const innerHeight = computed(() => chartHeight - marginTop - marginBottom)
    const bins = 24
    const barWidth = computed(() => Math.max(1, innerWidth.value / bins))
    const scoreHistogram = computed(() => {
      const arr = Array.from({ length: bins }, (_, i) => ({ x0: i / bins, x1: (i + 1) / bins, count: 0 }))
      for (const a of anomalyResults.value || []) {
        const s = Math.min(0.9999, Math.max(0, Number(a.score) || 0))
        const idx = Math.floor(s * bins)
        arr[idx].count += 1
      }
      return arr
    })
    const avgScore = computed(() => {
      const arr = anomalyResults.value || []
      if (!arr.length) return 0
      const sum = arr.reduce((acc, a) => acc + (Number(a.score) || 0), 0)
      return sum / arr.length
    })
    const histXTicks = computed(() => Array.from({ length: 11 }, (_, i) => i * 0.1))
    const xPos = (v) => marginLeft + Math.max(0, Math.min(innerWidth.value, v * innerWidth.value))
    const yGrid = (t) => marginTop + (innerHeight.value - innerHeight.value * t)
    const histYTicks = computed(() => [0, 0.25, 0.5, 0.75, 1])

    const severityBars = computed(() => {
      const order = [
        { key: '低', color: '#67C23A', label: '低' },
        { key: '中', color: '#E6A23C', label: '中' },
        { key: '高', color: '#F56C6C', label: '高' }
      ]
      const counts = { '低': 0, '中': 0, '高': 0 }
      for (const a of yAxisAnomalies.value || []) {
        if (counts[a.severity] !== undefined) counts[a.severity]++
      }
      return order.map(o => ({ ...o, count: counts[o.key] }))
    })
    const severityBarWidth = 80
    const maxHistCount = computed(() => Math.max(1, ...(scoreHistogram.value?.map(b => b.count) || [1])))
    const maxSevCount = computed(() => Math.max(1, ...(severityBars.value?.map(s => s.count) || [1])))
    const histHeight = (v) => Math.round((v / maxHistCount.value) * innerHeight.value)
    const sevHeight = (v) => Math.round((v / maxSevCount.value) * innerHeight.value)

    // Donut pie for severity proportion
    const toRad = (deg) => (deg * Math.PI) / 180
    const arcPath = (cx, cy, r, r0, start, end) => {
      // large-arc-flag
      const laf = end - start > Math.PI ? 1 : 0
      const x1 = cx + r * Math.cos(start)
      const y1 = cy + r * Math.sin(start)
      const x2 = cx + r * Math.cos(end)
      const y2 = cy + r * Math.sin(end)
      const x3 = cx + r0 * Math.cos(end)
      const y3 = cy + r0 * Math.sin(end)
      const x4 = cx + r0 * Math.cos(start)
      const y4 = cy + r0 * Math.sin(start)
      return `M ${x1} ${y1} A ${r} ${r} 0 ${laf} 1 ${x2} ${y2} L ${x3} ${y3} A ${r0} ${r0} 0 ${laf} 0 ${x4} ${y4} Z`
    }
    const currentYAxisTotal = computed(() => yAxisAnomalies.value.length)

    const severityPieArcs = computed(() => {
      const total = Math.max(1, currentYAxisTotal.value)
      // Fixed dimensions for pie chart to prevent clipping
      const svgWidth = 280
      const svgHeight = 280
      const centerX = svgWidth / 2
      const centerY = svgHeight / 2
      // Use fixed radius that we know fits
      const outerR = 100
      const innerR = 65
      let angle = -Math.PI / 2 // start at top
      const bars = severityBars.value || []
      const nonZero = bars.filter(b => (b.count || 0) > 0)
      const singleNonZeroKey = nonZero.length === 1 ? nonZero[0].key : null

      return bars.map(seg => {
        const rawPercent = (seg.count || 0) / total
        const percent = singleNonZeroKey && seg.key === singleNonZeroKey ? 1 : (singleNonZeroKey ? 0 : rawPercent)
        const full = Math.PI * 2
        const delta = percent >= 1 ? full - 1e-4 : percent * full
        const start = angle
        const end = angle + delta
        angle = end
        return {
          key: seg.key,
          color: seg.color,
          percent,
          d: arcPath(centerX, centerY, outerR, innerR, start, end)
        }
      })
    })
    const severityPieLegend = computed(() => {
      const total = Math.max(1, currentYAxisTotal.value)
      return severityBars.value.map(s => ({
        key: s.key,
        label: s.label,
        color: s.color,
        count: s.count || 0,
        percent: total ? (s.count || 0) / total : 0
      }))
    })

    const smallScreen = computed(() => chartWidthPie.value < 520)

    const scatterHasData = computed(() => {
      const s = scatterData.value
      if (!s) return false
      const normalCount = Array.isArray(s.normal_points) ? s.normal_points.length : 0
      const anomalyCount = Array.isArray(s.anomaly_points) ? s.anomaly_points.length : 0
      return normalCount + anomalyCount > 0
    })

    const scatterHasCorrectedData = computed(() => {
      const s = scatterData.value
      if (!s) return false
      const correctedCount = Array.isArray(s.corrected_points) ? s.corrected_points.length : 0
      const correctedAnomalyCount = Array.isArray(s.corrected_anomaly_points) ? s.corrected_anomaly_points.length : 0
      return correctedCount + correctedAnomalyCount > 0
    })

    // ECharts 散点图数据构建：将后端 normal/anomaly 及改正后的点转换为 [time, value, row_index]
    const buildScatterSeriesData = () => {
      const s = scatterData.value
      if (!s) {
        return { normal: [], anomaly: [], corrected: [], correctedAnomaly: [] }
      }

      const toSeries = (arr) => {
        return (arr || [])
          .filter(p => p && p.time != null && p.value != null)
          .map(p => [p.time, Number(p.value), p.row_index])
      }

      return {
        normal: toSeries(s.normal_points || []),
        anomaly: toSeries(s.anomaly_points || []),
        corrected: toSeries(s.corrected_points || []),
        correctedAnomaly: toSeries(s.corrected_anomaly_points || [])
      }
    }

    let scatterChartInstance = null
    let correctedScatterChartInstance = null

    const baseTimeValueAxes = (xLabel, yLabel) => ({
      xAxis: {
        type: 'time',
        name: xLabel,
        nameLocation: 'middle',
        nameGap: 35,
        axisLabel: {
          margin: 12,
          fontSize: 10,
          hideOverlap: true,
          formatter: (value, index) => {
            if (index % 4 !== 0) return ''
            const d = new Date(value)
            if (isNaN(d.getTime())) return ''
            return d.toLocaleDateString('zh-CN', {
              month: '2-digit',
              day: '2-digit'
            })
          }
        }
      },
      yAxis: {
        type: 'value',
        name: yLabel,
        nameLocation: 'end',
        nameGap: 16,
        nameTextStyle: {
          fontWeight: 'bold',
          fontSize: 13,
          align: 'center'
        }
      }
    })

    const baseStaticChartOptions = () => ({
      animation: false,
      animationDuration: 0,
      animationDurationUpdate: 0,
      progressive: 0,
      grid: { left: 60, right: 20, top: 40, bottom: 70 },
      tooltip: {
        trigger: 'item',
        formatter: (params) => {
          const data = params.data || []
          const time = data[0]
          const value = data[1]
          const rowIndex = data[2]
          const d = new Date(time)
          const timeStr = isNaN(d.getTime())
            ? String(time)
            : d.toLocaleString('zh-CN', {
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
              })
          return [
            `${params.seriesName} · 行 ${rowIndex}`,
            `时间：${timeStr}`,
            `数值：${value}`
          ].join('<br/>')
        }
      },
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: 0,
          zoomOnMouseWheel: true,
          moveOnMouseMove: true
        },
        {
          type: 'slider',
          xAxisIndex: 0,
          height: 20,
          bottom: 6,
          borderRadius: 8,
          backgroundColor: '#f5f7fa',
          dataBackground: {
            lineStyle: { color: 'rgba(144,147,153,0.4)' },
            areaStyle: { color: 'rgba(144,147,153,0.18)' }
          },
          fillerColor: 'rgba(194,122,59,0.25)',
          handleSize: 12,
          handleStyle: {
            color: '#fff',
            borderColor: 'var(--primary-color)',
            borderWidth: 1.2,
            shadowBlur: 4,
            shadowColor: 'rgba(194,122,59,0.35)'
          },
          textStyle: {
            color: '#909399',
            fontSize: 10
          }
        }
      ]
    })

    const updateScatterChart = () => {
      if (!scatterChartInstance && scatterChartRef.value) {
        scatterChartInstance = echarts.init(scatterChartRef.value)
      }
      if (!scatterChartInstance) return
      const s = scatterData.value
      if (!s) {
        scatterChartInstance.clear()
        return
      }
      const { normal, anomaly } = buildScatterSeriesData()
      const xLabel = s.x_label || '时间'
      const yLabel = s.y_label || '数值'

      scatterChartInstance.setOption({
        ...baseStaticChartOptions(),
        ...baseTimeValueAxes(xLabel, yLabel),
        series: [
          {
            name: '正常',
            type: 'scatter',
            symbolSize: 5,
            itemStyle: { color: 'rgba(59,130,246,0.85)' },
            data: showNormalPoints.value ? normal : []
          },
          {
            name: '异常',
            type: 'scatter',
            symbolSize: 7,
            itemStyle: { color: '#F56C6C' },
            data: showAnomalyPoints.value ? anomaly : []
          }
        ]
      })
    }

    const updateCorrectedScatterChart = () => {
      if (!correctedScatterChartInstance && correctedScatterChartRef.value) {
        correctedScatterChartInstance = echarts.init(correctedScatterChartRef.value)
      }
      if (!correctedScatterChartInstance) return
      const s = scatterData.value
      if (!s) {
        correctedScatterChartInstance.clear()
        return
      }
      const { corrected, correctedAnomaly } = buildScatterSeriesData()
      const xLabel = s.x_label || '时间'
      const yLabel = s.y_label || '数值'

      correctedScatterChartInstance.setOption({
        ...baseStaticChartOptions(),
        ...baseTimeValueAxes(xLabel, yLabel),
        series: [
          {
            name: '正常',
            type: 'scatter',
            symbolSize: 5,
            itemStyle: { color: 'rgba(59,130,246,0.85)' },
            data: showCorrectedTrack.value ? corrected : []
          },
          {
            name: '异常修正点',
            type: 'scatter',
            symbol: 'x',
            symbolSize: 8,
            itemStyle: { color: '#67C23A' },
            data: showCorrectedAnomaly.value ? correctedAnomaly : []
          }
        ]
      })
    }

    const severityPieLabels = computed(() => {
      const total = Math.max(1, anomalyResults.value.length)
      const centerX = chartWidthPie.value / 2
      const centerY = chartHeight / 2
      const safePad = 26
      const outerR = Math.min(chartWidthPie.value / 2 - safePad, chartHeight / 2 - safePad)
      const labelR = outerR + (smallScreen.value ? 8 : 14)
      let angle = -Math.PI / 2
      return severityBars.value.map(seg => {
        const percent = (seg.count || 0) / total
        const delta = percent * Math.PI * 2
        const mid = angle + delta / 2
        let x = centerX + labelR * Math.cos(mid)
        let y = centerY + labelR * Math.sin(mid)
        const anchor = Math.cos(mid) >= 0 ? 'start' : 'end'
        const lx = centerX + outerR * Math.cos(mid)
        const ly = centerY + outerR * Math.sin(mid)
        angle += delta
        // skip tiny slices or when small
        if (percent < 0.06 || smallScreen.value) return null
        // clamp inside svg bounds with padding
        const pad = 8
        x = Math.max(pad, Math.min(chartWidthPie.value - pad, x))
        y = Math.max(12, Math.min(chartHeight - pad, y))
        return { key: seg.key, color: seg.color, text: `${seg.label} ${Math.round(percent*100)}%`, x, y, anchor, lx, ly }
      })
    })

    const histWrapper = ref(null)
    const pieWrapper = ref(null)
    const sevWrapper = ref(null)
    let resizeObserver = null
    const startResizeObserver = () => {
      const targets = [
        pieWrapper.value,
        sevWrapper.value,
        scatterWrapper.value,
        correctedScatterWrapper.value,
        compareTableWrapper.value
      ].filter(Boolean)
      if (targets.length === 0) return
      resizeObserver = new ResizeObserver(entries => {
        for (const e of entries) {
          const w = Math.max(360, Math.floor(e.contentRect.width))
          if (e.target === pieWrapper.value) {
            chartWidthPie.value = w
          } else if (e.target === sevWrapper.value) {
            chartWidth.value = w
          } else if (e.target === scatterWrapper.value) {
            chartWidthScatter.value = w
            if (scatterChartInstance) {
              scatterChartInstance.resize()
            }
          } else if (e.target === correctedScatterWrapper.value) {
            chartWidthScatter.value = w
            if (correctedScatterChartInstance) {
              correctedScatterChartInstance.resize()
            }
          } else if (e.target === compareTableWrapper.value) {
            // 底部对比表格容器宽度发生变化（如侧边栏收缩/展开），强制重算表格列宽
            if (anomalyTableRef.value && typeof anomalyTableRef.value.doLayout === 'function') {
              anomalyTableRef.value.doLayout()
            }
          }
        }
      })
      for (const t of targets) resizeObserver.observe(t)
    }

    onMounted(async () => {
      await nextTick()
      startResizeObserver()
      if (scatterChartRef.value) {
        scatterChartInstance = echarts.init(scatterChartRef.value)
        updateScatterChart()
      }
      if (correctedScatterChartRef.value) {
        correctedScatterChartInstance = echarts.init(correctedScatterChartRef.value)
        updateCorrectedScatterChart()
      }
    })

    onBeforeUnmount(() => {
      if (resizeObserver) resizeObserver.disconnect()
      if (scatterChartInstance) {
        scatterChartInstance.dispose()
        scatterChartInstance = null
      }
      if (correctedScatterChartInstance) {
        correctedScatterChartInstance.dispose()
        correctedScatterChartInstance = null
      }
      clearTaskTimer()
    })

    watch([scatterData, showNormalPoints, showAnomalyPoints], () => {
      nextTick().then(() => {
        updateScatterChart()
      })
    })

    watch([scatterData, showCorrectedTrack, showCorrectedAnomaly], () => {
      nextTick().then(() => {
        updateCorrectedScatterChart()
      })
    })

    // 标志：是否正在加载模板
    let isLoadingTemplate = false
    // 标志：是否正在使用模板
    const isUsingTemplate = ref(false)
    
    // 监听文件选择变化：不再自动加载，只清空已加载的信息与选择
    watch(selectedFileId, (newVal, oldVal) => {
      // 如果是模板加载导致的文件ID变化，不清空结果数据
      if (isLoadingTemplate) {
        isLoadingTemplate = false
        return
      }
      
      // 清空之前的文件信息与特征选择，等待用户点击“加载文件信息”
      fileInfo.value = null
      detectionConfig.value.targetFeature = []
      isAllSelected.value = false
      anomalyResults.value = []
      detectionTime.value = 0
      scatterData.value = null
    })

    // 保存为模板
    const saveAsTemplate = async () => {
      const templateName = prompt('请输入模板名称：')
      if (!templateName) return
      
      // 检查是否有结果可以保存
      if (!anomalyResults.value.length) {
        ElMessage.warning('请先执行异常检测，获取结果后再保存模板')
        return
      }
      
      // 不再检查散点图数据，因为不保存散点图数据
      
      // 设置保存模板状态为运行中
      saveTemplateStatus.value = 'running'
      saveTemplateProgress.value = 0
      
      // 不生成所有特征列的散点图数据，因为不保存散点图数据
      saveTemplateProgress.value = 0.7
      
      // 创建模板对象，保存完整的模板内容
      const templateData = {
        name: templateName,
        type: 'anomaly',
        config: {
          fileId: selectedFileId.value,
          method: detectionConfig.value.method,
          features: [...detectionConfig.value.targetFeature],
          contamination: detectionConfig.value.contamination,
          n_estimators: detectionConfig.value.n_estimators,
          max_samples: detectionConfig.value.max_samples
        },
        results: {
          anomalyResults: [...anomalyResults.value], // 保存所有异常结果
          detectionTime: detectionTime.value,
          lastCorrectedFilePath: lastCorrectedFilePath.value,
          lastAnomalyIndices: [...lastAnomalyIndices.value], // 保存所有异常索引
          featureAnomaliesMap: { ...featureAnomaliesMap.value },
          fileInfo: fileInfo.value, // 保存完整的文件信息
          // 保存模板创建时的原文件ID和名称，用于加载时检查
          originalFile: {
            id: selectedFileId.value,
            name: fileInfo.value?.original_filename || selectedFileId.value
          },
          // 保存当前选中的Y轴特征，以便加载模板时恢复
          selectedYAxisFeature: selectedYAxisFeature.value,
          // 保存散点图开关状态
          showNormalPoints: showNormalPoints.value,
          showAnomalyPoints: showAnomalyPoints.value,
          showCorrectedTrack: showCorrectedTrack.value,
          showCorrectedAnomaly: showCorrectedAnomaly.value
          // 不保存散点图数据，加载时自动生成
        }
      }
      
      try {
        // 更新进度
        saveTemplateProgress.value = 0.8
        console.log('开始保存模板到后端，模板数据大小:', JSON.stringify(templateData).length, '字节')
        
        // 保存到后端API，添加超时处理
        const response = await templateApi.createTemplate(templateData)
        console.log('模板保存成功，后端响应:', response)
        
        // 更新进度
        saveTemplateProgress.value = 1.0
        saveTemplateStatus.value = 'finished'
        
        ElMessage.success('模板保存成功，包含完整分析结果')
        // 重新加载模板列表
        loadHistoryTemplates()
      } catch (error) {
        console.error('保存模板失败:', error)
        console.error('错误详情:', error.response || error.message || error)
        saveTemplateStatus.value = 'failed'
        ElMessage.error('保存模板失败：' + (error.message || '未知错误'))
      } finally {
        // 延迟重置状态，让用户看到完成状态
        setTimeout(() => {
          saveTemplateStatus.value = 'idle'
          saveTemplateProgress.value = 0
        }, 1000)
      }
    }
    
    // 加载模板
    // 为指定特征生成散点图数据（无提示）
    const generateScatterDataForFeature = async (feature) => {
      try {
        let indices = []
        const map = featureAnomaliesMap.value || {}
        if (Array.isArray(map[feature]) && map[feature].length) {
          indices = map[feature].map(n => Number(n))
        } else {
          indices = (anomalyResults.value || [])
            .filter(a => {
              const triggers = a.trigger_features || []
              if (!Array.isArray(triggers) || triggers.length === 0) return false
              return triggers.includes(feature)
            })
            .map(a => a.row_index)
        }

        // 检查是否有文件信息
        if (!fileInfo.value || !fileInfo.value.id) {
          console.error('缺少文件信息，无法生成散点图数据')
          return
        }

        const resp = await api.analysis.regenerateScatter({
          base_file_id: fileInfo.value.id,
          corrected_file_path: lastCorrectedFilePath.value,
          y_axis_feature: feature,
          anomaly_indices: indices,
        })

        if (resp && resp.success && resp.data) {
          scatterData.value = resp.data
          allScatterData.value[feature] = resp.data
        }
      } catch (err) {
        console.error(`生成特征 ${feature} 的散点图数据失败:`, err)
      }
    }
    
    // 直接生成散点图，不经过重新加载文件（无提示）
    const generateScatterDirectly = async (feature) => {
      try {
        await generateScatterDataForFeature(feature)
      } catch (err) {
        console.error('直接生成散点图失败:', err)
      }
    }
    
    const loadTemplate = async (template) => {
      // 设置模板加载标志
      isLoadingTemplate = true
      isUsingTemplate.value = true
      
      // 加载模板配置
      detectionConfig.value.method = template.config.method
      detectionConfig.value.targetFeature = [...template.config.features]
      detectionConfig.value.contamination = template.config.contamination
      detectionConfig.value.n_estimators = template.config.n_estimators
      detectionConfig.value.max_samples = template.config.max_samples
      
      // 更新全选状态
      handleFeatureSelect()
      
      // 如果模板包含结果数据，加载结果
      if (template.results) {
        // 直接使用模板中保存的结果数据
        anomalyResults.value = [...template.results.anomalyResults]
        detectionTime.value = template.results.detectionTime
        lastCorrectedFilePath.value = template.results.lastCorrectedFilePath
        lastAnomalyIndices.value = [...template.results.lastAnomalyIndices]
        featureAnomaliesMap.value = { ...template.results.featureAnomaliesMap }
        
        // 检查模板创建时的原文件是否存在
        const originalFile = template.results.originalFile
        if (originalFile) {
          try {
            // 尝试检查原文件是否存在
            await api.file.getFileInfo(String(originalFile.id))
            // 原文件存在，继续加载
            if (template.results.fileInfo) {
              // 保存模板中原始的文件信息
              const originalFileInfo = template.results.fileInfo
              fileInfo.value = originalFileInfo
              selectedFileId.value = originalFileInfo.id
              
              // 自动加载文件信息，模拟点击了加载文件信息按钮
              await loadFileInfo(originalFileInfo.id)
            } else {
              // 如果模板中没有文件信息，尝试从配置中获取
              if (template.config.fileId) {
                // 创建一个基本的文件信息对象
                const basicFileInfo = {
                  id: template.config.fileId,
                  name: template.config.fileId,
                  original_name: template.config.fileId,
                  size: 0,
                  type: 'csv',
                  path: template.config.fileId
                }
                fileInfo.value = basicFileInfo
                selectedFileId.value = template.config.fileId
                
                // 自动加载文件信息，模拟点击了加载文件信息按钮
                await loadFileInfo(template.config.fileId)
              }
            }
          } catch (error) {
            // 原文件不存在，给出明确的提示
            console.error('原文件不存在，无法加载:', error)
            ElMessage.error(`原文件 ${originalFile.name} 已被删除，无法加载`)
            // 保持模板中保存的文件信息，但不尝试加载实际文件
            if (template.results.fileInfo) {
              fileInfo.value = template.results.fileInfo
              selectedFileId.value = template.results.fileInfo.id
            }
          }
        } else {
          // 模板中没有保存原文件信息，继续尝试加载
          if (template.results.fileInfo) {
            // 保存模板中原始的文件信息
            const originalFileInfo = template.results.fileInfo
            fileInfo.value = originalFileInfo
            selectedFileId.value = originalFileInfo.id
            
            try {
              // 尝试加载文件信息，模拟点击了加载文件信息按钮
              await loadFileInfo(originalFileInfo.id)
            } catch (error) {
              // 加载失败时，保持模板中保存的文件信息
              console.error('加载文件信息失败，保持模板中保存的文件信息:', error)
              // 不重置任何状态，使用模板中保存的文件信息
            }
          } else {
            // 如果模板中没有文件信息，尝试从配置中获取
            if (template.config.fileId) {
              // 创建一个基本的文件信息对象
              const basicFileInfo = {
                id: template.config.fileId,
                name: template.config.fileId,
                original_name: template.config.fileId,
                size: 0,
                type: 'csv',
                path: template.config.fileId
              }
              fileInfo.value = basicFileInfo
              selectedFileId.value = template.config.fileId
              
              try {
                // 尝试加载文件信息，模拟点击了加载文件信息按钮
                await loadFileInfo(template.config.fileId)
              } catch (error) {
                // 加载失败时，保持基本的文件信息对象
                console.error('加载文件信息失败，保持基本的文件信息:', error)
                // 不重置任何状态，使用基本的文件信息对象
              }
            }
          }
        }
        
        // 加载选中的Y轴特征
        if (template.results.selectedYAxisFeature) {
          selectedYAxisFeature.value = template.results.selectedYAxisFeature
        } else if (detectionConfig.value.targetFeature.length > 0) {
          // 否则选择第一个特征列
          selectedYAxisFeature.value = detectionConfig.value.targetFeature[0]
        }
        
        // 加载散点图开关状态
        if (template.results.showNormalPoints !== undefined) {
          showNormalPoints.value = template.results.showNormalPoints
        }
        if (template.results.showAnomalyPoints !== undefined) {
          showAnomalyPoints.value = template.results.showAnomalyPoints
        }
        if (template.results.showCorrectedTrack !== undefined) {
          showCorrectedTrack.value = template.results.showCorrectedTrack
        }
        if (template.results.showCorrectedAnomaly !== undefined) {
          showCorrectedAnomaly.value = template.results.showCorrectedAnomaly
        }
        
        // 自动生成散点图数据，不显示提示
        if (fileInfo.value && selectedYAxisFeature.value) {
          await generateScatterDataForFeature(selectedYAxisFeature.value)
        }
        
        ElMessage.success('模板加载成功，已显示分析结果')
      } else {
        // 重置结果数据
        anomalyResults.value = []
        scatterData.value = null
        allScatterData.value = {} // 清空所有散点图数据
        detectionTime.value = 0
        lastCorrectedFilePath.value = ''
        lastAnomalyIndices.value = []
        featureAnomaliesMap.value = {}
        selectedYAxisFeature.value = ''
        
        // 重置散点图开关状态
        showNormalPoints.value = true
        showAnomalyPoints.value = true
        showCorrectedTrack.value = true
        showCorrectedAnomaly.value = true
        
        // 清空fileInfo和selectedFileId
        fileInfo.value = null
        selectedFileId.value = ''
        
        ElMessage.success('模板加载成功，请点击执行按钮进行分析')
      }
    }
    
    // 删除模板
    const deleteTemplate = async (templateId) => {
      if (confirm('确定要删除该模板吗？')) {
        try {
          await templateApi.deleteTemplate(templateId)
          ElMessage.success('模板删除成功')
          // 重新加载模板列表
          loadHistoryTemplates()
        } catch (error) {
          console.error('删除模板失败:', error)
          ElMessage.error('删除模板失败，请重试')
        }
      }
    }
    
    // 加载历史模板
    const loadHistoryTemplates = async () => {
      try {
        const response = await templateApi.getTemplates('anomaly')
        historyTemplates.value = response.data || []
      } catch (error) {
        console.error('加载模板失败:', error)
        historyTemplates.value = []
        ElMessage.error('加载模板失败: ' + (error.message || '未知错误'))
      }
    }
    
    // 处理模板排序
    const handleTemplateSort = ({ field, order }) => {
      templateSort.value = { prop: field, order }
    }
    
    // 编辑模板名称
    const editTemplateName = async (template) => {
      if (!template) return
      
      const newName = prompt('请输入新的模板名称：', template.name)
      if (!newName || newName.trim() === template.name) return
      
      try {
        await templateApi.updateTemplateName(template.id, newName.trim())
        ElMessage.success('模板名称修改成功')
        // 重新加载模板列表
        loadHistoryTemplates()
      } catch (error) {
        console.error('修改模板名称失败:', error)
        ElMessage.error('修改模板名称失败，请重试')
      }
    }
    
    // 组件挂载时加载文件列表和历史模板
    onMounted(() => {
      loadAvailableFiles()
      loadHistoryTemplates()
    })

    return {
      selectedFileId,
      availableFiles,
      fileInfo,
      anomalyResults,
      detectionTime,
      featureDetailsVisible,
      selectedAnomaly,
      activeCollapseNames,
      detectionConfig,
      isUsingTemplate,
      chartWidth,
      chartHeight,
      generateScatterDirectly,
      // 历史模板相关
      historyTemplates,
      templateSearchKeyword,
      templateSort,
      filteredTemplates,
      handleTemplateSort,
      editTemplateName,
      marginTop,
      marginRight,
      marginBottom,
      marginLeft,
      innerWidth,
      innerHeight,
      barWidth,
      histHeight,
      sevHeight,
      scoreHistogram,
      severityBars,
      severityBarWidth,
      maxHistCount,
      maxSevCount,
      maxSampleOptions,
      isAllSelected,
      numericColumns,
      isReady,
      isDetecting,
      canSaveTemplate,
      featureSearchKeyword,
      filteredFeatureColumns,
      displayedFeatureTags,
      avgScore,
      histXTicks,
      histYTicks,
      xPos,
      yGrid,
      severityPieArcs,
      severityPieLegend,
      currentYAxisTotal,
      severityPieLabels,
      smallScreen,
      taskStatus,
      taskProgress,
      scatterHasData,
      scatterHasCorrectedData,
      histWrapper,
      pieWrapper,
      sevWrapper,
      scatterWrapper,
      scatterChartRef,
      correctedScatterWrapper,
      correctedScatterChartRef,
      selectedYAxisFeature,
      showNormalPoints,
      showAnomalyPoints,
      showCorrectedTrack,
      showCorrectedAnomaly,
      chartWidthScatter,
      formatFileSize,
      formatDateTime,
      loadFileInfo,
      handleSelectAll,
      handleFeatureSelect,
      updateSelectAllStatus,
      resetConfig,
      runDetection,
      getMethodName,
      getAnomalyPercentage,
      getSeverityType,
      getProgressColor,
      truncateText,
      removeFeature,
      showFeatureDetails,
      getFeatureTableData,
      // 历史模板相关
      historyTemplates,
      saveAsTemplate,
      loadTemplate,
      deleteTemplate,
      saveTemplateStatus,
      saveTemplateProgress,
      // kpi & filters（仅底部对比表格）
      selectedCompareSeverities,
      // 搜索与分页
      compareSearchTextInput,
      compareSearchText,
      sortedCompareRows,
      pagedCompareRows,
      compareCurrentPage,
      comparePageSize,
      comparePageSizes,
      handleComparePageSizeChange,
      handleCompareSortChange,
      // expose for template bindings
      isNumericType,
      dataTypes,
      scatterData,
      lastCorrectedFilePath,
      lastAnomalyIndices,
      compareTableWrapper, // Add this line
    }
  }
}
</script>

<style scoped>
.anomaly-container {
  padding: 20px;
}

.anomaly-container h1 {
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

/* 模板搜索栏样式 */
.template-search-bar {
  margin-bottom: 16px;
  display: flex;
  justify-content: flex-end;
}

.template-search-input {
  width: 240px;
}

/* 表格样式美化 */
:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

:deep(.el-table__header-wrapper) {
  background-color: #fafafa;
}

:deep(.el-table__header th) {
  background-color: #fafafa;
  font-weight: 600;
  color: #303133;
  border-bottom: 2px solid #ebeef5;
}

:deep(.el-table__body tr:hover > td) {
  background-color: #f5f7fa;
}

:deep(.el-table__body tr) {
  transition: all 0.3s ease;
}

:deep(.el-table__body tr:nth-child(even)) {
  background-color: #fafafa;
}

/* 操作按钮样式 */
:deep(.el-button--small) {
  margin-right: 8px;
  border-radius: 4px;
  transition: all 0.3s ease;
}

:deep(.el-button--small:hover) {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}



.data-source-selector {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  flex-wrap: nowrap;
}

/* 与预处理保持一致：选择框占满，按钮固定最小宽度 */
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

@media (max-width: 720px) {
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

.params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 25px;
}

.select-all-container {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.feature-list {
  margin-bottom: 15px;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #ebeef5;
  padding: 15px;
  border-radius: 4px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

/* 异常检测页面特殊的已选择特征样式 */
.selected-features-display {
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
  max-height: 120px;
  overflow-y: auto;
}

.selection-label {
  margin-right: 10px;
  font-weight: 500;
  color: #606266;
}

.results-content {
  padding: 8px 0 4px;
}

/* 底部对比模块：表头（搜索+选择器）与表格之间留出更大缝隙 */
.compare-section > .chart-header {
  margin-bottom: 16px;
}

/* 任务进度条：更细、更圆角、带轻微背景；与其它模块保持统一的垂直间距 */
.task-progress-bar {
  margin-top: 0;
  padding: 8px 12px;
  border-radius: 10px;
  background: rgba(37, 99, 235, 0.04);
}

.task-progress-bar.top {
  margin-top: 0;
}

.task-progress-text {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #4b5563;
  margin-bottom: 6px;
}

.task-progress-text span:last-child {
  opacity: 0.9;
}

.task-progress-bar :deep(.el-progress-bar__outer) {
  border-radius: 999px;
}

.task-progress-bar :deep(.el-progress-bar__inner) {
  border-radius: 999px;
  background-image: linear-gradient(90deg, #60a5fa, #2563eb);
}

.compare-pagination {
  margin-top: 8px;
  text-align: right;
}

/* Charts Section */
.charts-section-card {
  margin-bottom: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  padding: 8px 16px 14px;
}

.charts-two-col {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 24px;
  padding: 4px 0 6px;
}

@media (max-width: 1200px) {
  .charts-two-col {
    grid-template-columns: 1fr;
  }
}

.chart-col {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
}

/* 让散点图在栅格中占满整行，使视图更宽、更清晰 */
.scatter-col {
  grid-column: 1 / -1;
}

/* ECharts 容器：保证有明确高度，否则图会不显示 */
.scatter-wrapper {
  align-items: stretch;
}

.scatter-svg-container {
  flex: 1 1 auto;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.scatter-echart {
  width: 100%;
  height: 360px;
  border: 1px solid #f0f0f0;
}

/* 饼图图例样式 */
.legend-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 2px;
}

.legend-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.legend-text {
  flex: 1;
}

.legend-label {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 2px;
}

.legend-value {
  font-size: 12px;
  color: #909399;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-left: 12px;
  border-left: 4px solid var(--primary-color);
}

.chart-axis-title {
  font-size: 13px;
  fill: #606266;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.chart-axis-text {
  font-size: 12px;
  fill: #909399;
  font-weight: 500;
  paint-order: stroke;
  stroke: rgba(255,255,255,0.7);
  stroke-width: 2px;
}

/* Pie Chart with Vertical Legend */
.pie-chart-container {
  display: flex;
  align-items: center;
  gap: 40px;
  justify-content: center;
  min-height: 320px;
  padding: 20px;
}

.pie-svg-wrapper {
  flex: 0 0 auto;
  width: 280px;
  height: 280px;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: visible !important;
}

.pie-svg-wrapper svg {
  display: block;
  max-width: 100%;
  height: auto;
}

.pie-legend-vertical {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 0 0 auto;
  min-width: 140px;
}

/* 表头通用布局 */
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-header .header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: nowrap;
}

.index-search-input {
  max-width: 260px;
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 20px;
}

@media (max-width: 980px) {
  .charts-two-col {
    grid-template-columns: 1fr;
  }
  
  .pie-chart-container {
    flex-direction: column;
  }
}

/* 严重程度选择器（底部）：统一为扁平分段控件样式 */
.sev-group {
  display: inline-flex;
  align-items: center;
  gap: 0;
  padding: 0;
  border-radius: 4px;
  background: transparent;
  overflow: hidden;
}

.sev-group :deep(.el-checkbox-button) {
  margin: 0;
  flex: 1 1 0;
}

.sev-group :deep(.el-checkbox-button__inner) {
  border-radius: 0 !important;
  border: 1px solid var(--primary-color);
  padding: 4px 18px;
  font-size: 12px;
  line-height: 1.2;
  color: var(--primary-color);
  background-color: #ffffff;
  border-left-width: 0;
  width: 100%;
  box-sizing: border-box;
  justify-content: center;
}

.sev-group :deep(.el-checkbox-button:first-child .el-checkbox-button__inner) {
  border-top-left-radius: 4px !important;
  border-bottom-left-radius: 4px !important;
  border-left-width: 1px;
}

.sev-group :deep(.el-checkbox-button:last-child .el-checkbox-button__inner) {
  border-top-right-radius: 4px !important;
  border-bottom-right-radius: 4px !important;
}

.sev-group :deep(.el-checkbox-button.is-checked .el-checkbox-button__inner) {
  background: var(--primary-color);
  color: #ffffff;
}

.sev-group :deep(.el-checkbox-button__inner:hover) {
  background-color: rgba(249, 115, 22, 0.06);
}

.scatter-yaxis-selector {
  display: flex;
  align-items: center;
}

.scatter-yaxis-selector :deep(.el-select) {
  min-width: 220px;
}

.scatter-yaxis-selector :deep(.el-select .el-input__wrapper) {
  padding: 2px 12px;
  border-radius: 999px;
}

.chart-wrapper {
  min-height: 360px;
  display: flex;
  justify-content: center;
  align-items: center;
  background: transparent;
  border-radius: 8px;
  box-shadow: none;
  padding: 8px;
  overflow: visible !important;
}

.chart-placeholder {
  color: #909399;
  font-size: 14px;
}

.score-display {
  display: flex;
  align-items: center;
  gap: 10px;
}

.score-value {
  font-weight: bold;
  min-width: 60px;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.slider-label {
  flex: 0 0 auto;
  min-width: 100px;
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.slider-control {
  flex: 1 1 auto;
}

.dialog-footer {
  text-align: right;
}

.config-section {
  padding: 10px 0;
}

.mb-1 {
  margin-bottom: 8px;
}

.mb-3 {
  margin-bottom: 16px;
}

.block {
  display: block;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .anomaly-container {
    padding: 10px;
  }
  
  .params-grid {
    grid-template-columns: 1fr;
  }
}

/* 响应式优化 */
@media screen and (max-width: 768px) {
  .anomaly-container {
    padding: 10px;
  }
  
  .data-source-selector {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .data-source-selector > :deep(.el-select),
  .data-source-selector > :deep(.el-button) {
    width: 100%;
    min-width: 0;
  }

  .action-buttons {
    flex-direction: column;
    gap: 10px;
  }
}
</style>