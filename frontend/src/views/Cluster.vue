<template>
  <div class="cluster-container">
    <h1>聚类分析</h1>
    
    <!-- 数据源选择：对齐预处理模块 -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header"><span>数据源选择</span></div>
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
        <el-button type="primary" @click="loadFileInfo" :disabled="!selectedFileId" class="ds-button">加载文件信息</el-button>
      </div>
    </el-card>

    <!-- 文件信息：对齐预处理模块 -->
    <el-card shadow="never" v-if="fileInfo">
      <template #header>
        <div class="card-header"><span>文件信息</span></div>
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

    <!-- 地图数据（GeoJSON） -->
    <el-card shadow="never" v-if="fileInfo">
      <template #header>
        <div class="card-header"><span>地图数据（GeoJSON）</span></div>
      </template>
      <div class="data-source-selector horizontal">
        <el-select
          v-model="selectedGeojsonId"
          placeholder="选择地图 GeoJSON/JSON 文件"
          class="ds-select"
          @change="updateVisualization"
          filterable
        >
          <el-option
            v-for="file in geojsonFiles"
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
        <el-button
          type="primary"
          @click="loadGeojsonFiles"
          :loading="isLoadingGeojson"
          class="ds-button"
        >
          加载地图文件
        </el-button>
      </div>
    </el-card>
    
    <!-- 聚类配置 -->
    <el-card shadow="never" v-if="fileInfo">
      <template #header>
        <div class="card-header"><span>聚类配置</span></div>
      </template>
      
      <el-collapse v-model="activeCollapseNames" class="config-collapse">
        <el-collapse-item title="地区选择" name="features">
          <div class="config-section">
            <div class="feature-selection-area">
              <div class="select-all-container">
                <el-checkbox v-model="isAllFeaturesSelected" @change="handleFeaturesSelectAll" size="small" :disabled="isUsingTemplate">全选</el-checkbox>
                <el-input
                  v-model="featureSearchKeyword"
                  size="small"
                  placeholder="搜索地区"
                  clearable
                  class="area-search-input"
                />
              </div>
              <div class="feature-list">
                <el-checkbox-group v-model="clusterConfig.features" @change="handleFeaturesSelect" :disabled="isUsingTemplate">
                  <template v-for="feature in filteredFeatures" :key="feature">
                    <el-tooltip :disabled="isNumericType(dataTypes?.[feature])" content="非数值列无法参与本算法" placement="top">
                      <el-checkbox :label="feature" size="small" class="feature-checkbox" :disabled="!isNumericType(dataTypes?.[feature]) || isUsingTemplate">{{ feature }}</el-checkbox>
                    </el-tooltip>
                  </template>
                </el-checkbox-group>
              </div>
              <div class="selected-features-display" v-if="clusterConfig.features.length > 0">
                <span class="selection-label">已选择地区：</span>
                <el-tag v-for="feature in displayedClusterTags" :key="feature" :closable="!isUsingTemplate" @close="removeFeature(feature)" size="small" :title="feature" class="feature-tag">{{ feature }}</el-tag>
              </div>
            </div>
          </div>
        </el-collapse-item>
        
        <el-collapse-item title="聚类模式" name="algorithm">
          <div class="config-section">
            <div class="algorithm-selector">
              <el-select v-model="clusterConfig.algorithm" placeholder="选择聚类算法" style="width: 100%">
                <el-option label="K-means" value="kmeans">
                  <div class="algorithm-option">
                    <span class="algorithm-name">K-means</span>
                    <span class="algorithm-desc">基于距离的经典聚类算法</span>
                  </div>
                </el-option>
                <el-option label="层次聚类" value="hierarchical">
                  <div class="algorithm-option">
                    <span class="algorithm-name">层次聚类</span>
                    <span class="algorithm-desc">构建聚类层次的算法</span>
                  </div>
                </el-option>
                <el-option label="GMM" value="gmm">
                  <div class="algorithm-option">
                    <span class="algorithm-name">GMM</span>
                    <span class="algorithm-desc">高斯混合模型聚类</span>
                  </div>
                </el-option>
              </el-select>
            </div>
          </div>
        </el-collapse-item>
        
        <el-collapse-item title="算法参数" name="parameters">
          <div class="config-section">
            <div class="params-grid">
              <template v-if="clusterConfig.algorithm === 'kmeans'">
                <div class="param-item">
                  <label class="param-label">聚类数量</label>
                  <el-input-number v-model="clusterConfig.nClusters" :min="2" :max="50" />
                </div>
                <div class="param-item">
                  <label class="param-label">最大迭代次数</label>
                  <el-input-number v-model="clusterConfig.maxIter" :min="10" :max="1000" :step="10" />
                </div>
              </template>
              <!-- 层次聚类参数 -->
              <template v-if="clusterConfig.algorithm === 'hierarchical'">
                <div class="param-item">
                  <label class="param-label">聚类数量</label>
                  <el-input-number v-model="clusterConfig.nClusters" :min="2" :max="50" />
                </div>
                <div class="param-item">
                  <label class="param-label">链接方式</label>
                  <el-select v-model="clusterConfig.linkage" style="width: 100%">
                    <el-option label="ward" value="ward" />
                    <el-option label="average" value="average" />
                    <el-option label="complete" value="complete" />
                    <el-option label="single" value="single" />
                  </el-select>
                </div>
              </template>
              <template v-if="clusterConfig.algorithm === 'gmm'">
                <div class="param-item">
                  <label class="param-label">聚类数量</label>
                  <el-input-number v-model="clusterConfig.nClusters" :min="2" :max="50" />
                </div>
                <div class="param-item">
                  <label class="param-label">协方差类型</label>
                  <el-select v-model="clusterConfig.covarianceType" style="width: 100%">
                    <el-option label="full" value="full" />
                    <el-option label="tied" value="tied" />
                    <el-option label="diag" value="diag" />
                    <el-option label="spherical" value="spherical" />
                  </el-select>
                </div>
              </template>
              <div class="param-item">
                <label class="param-label">随机种子</label>
                <el-input-number v-model="clusterConfig.randomState" :min="0" :max="9999" />
              </div>
              <!-- 降维方法参数 -->
              <div class="param-item">
                <label class="param-label">降维方法</label>
                <el-select v-model="clusterConfig.dimensionalityReduction" style="width: 100%">
                  <el-option label="无" value="none" />
                  <el-option label="PCA" value="pca" />
                </el-select>
              </div>
              <div class="param-item" v-if="clusterConfig.dimensionalityReduction === 'pca'">
                <label class="param-label">PCA维度</label>
                <el-input-number v-model="clusterConfig.pcaComponents" :min="2" :max="50" />
              </div>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- 执行按钮 -->
    <el-card shadow="never" class="execute-card" v-if="fileInfo">
      <template #header>
        <div class="card-header"><span>执行聚类</span></div>
      </template>
      <div class="action-buttons">
        <el-button size="large" @click="runClustering" :loading="isClustering">执行</el-button>
        <el-button size="large" @click="saveAsTemplate" :disabled="!canRunCluster || !hasResults || !clusterResult">保存为模板</el-button>
        <el-button size="large" @click="estimateK" v-if="clusterConfig.algorithm === 'kmeans'" :disabled="!canEstimateK" :loading="isEstimatingK">估计最佳K值</el-button>
        <el-button size="large" @click="resetConfig">重置</el-button>
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
          <vxe-table-column field="name" title="模板名称" min-width="150" resizeable="false" sortable @sort-change="handleTemplateSort" />
          <vxe-table-column field="created_at" title="创建时间" sortable @sort-change="handleTemplateSort" min-width="180" resizeable="false">
            <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
          </vxe-table-column>
          <vxe-table-column field="config.algorithm" title="算法" min-width="120" resizeable="false">
            <template #default="{ row }">{{ row.config.algorithm }}</template>
          </vxe-table-column>
          <vxe-table-column field="config.features" title="特征数量" align="center" min-width="100" resizeable="false">
            <template #default="{ row }">{{ (row.config.features || []).length }}</template>
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
    
    <!-- K值估计结果 -->
    <el-card shadow="never" v-if="showKEstimation">
      <template #header>
        <div class="card-header"><span>K值估计结果</span></div>
      </template>
      <div class="k-estimation-result">
        <el-table :data="kEstimationData.results" style="width: 100%">
          <el-table-column prop="k" label="K值" width="80" align="center" />
          <el-table-column prop="inertia" label="惯性值" width="150" align="center">
            <template #default="scope">{{ scope.row.inertia.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="silhouette_score" label="轮廓系数" width="150" align="center">
            <template #default="scope">{{ scope.row.silhouette_score.toFixed(4) }}</template>
          </el-table-column>
          <el-table-column prop="davies_bouldin_score" label="DB指数" width="150" align="center">
            <template #default="scope">{{ scope.row.davies_bouldin_score.toFixed(4) }}</template>
          </el-table-column>
          <el-table-column prop="calinski_harabasz_score" label="CH指数" align="center">
            <template #default="scope">{{ scope.row.calinski_harabasz_score.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="推荐" width="100" align="center">
            <template #default="scope"><el-tag v-if="scope.row.is_recommended" type="success">推荐</el-tag></template>
          </el-table-column>
        </el-table>
        <div class="k-metrics-explanation">
          <p><strong>各指标含义：</strong></p>
          <p><strong>惯性值</strong>：所有样本到各自聚类中心的距离平方和，反映簇内的紧凑程度，一般越小越好。常用“肘部法则”观察随 K 增大时惯性值下降的拐点。</p>
          <p><strong>轮廓系数</strong>：综合衡量“簇内紧凑 + 簇间分离”的指标，取值通常在 [-1, 1]，越接近 1 说明聚类效果越好，接近 0 表示簇之间重叠，小于 0 表示很多点被分错簇。</p>
          <p><strong>DB 指数</strong>（Davies–Bouldin 指数）：刻画各簇之间“相似度”的指标，考虑簇内散度与簇间距离，一般越小越好，说明簇之间更分离、簇内更紧凑。</p>
          <p><strong>CH 指数</strong>（Calinski–Harabasz 指数）：又称方差比准则，衡量“簇间离散度 / 簇内离散度”的比值，一般越大越好，说明簇之间差异更明显。</p>
          <p><strong>推荐</strong>：综合上面多个指标（例如：惯性值的肘部位置、轮廓系数和 CH 指数的高值、DB 指数的低值）自动给出的参考 K 值，并不绝对，仍可结合业务按需调整。</p>
        </div>
      </div>
    </el-card>
    
    <!-- 聚类结果 -->
    <el-card shadow="never" v-if="hasResults">
      <template #header>
        <div class="card-header">
          <span>聚类结果</span>
          <div class="header-actions">

          </div>
        </div>
      </template>
      
      <!-- 结果标签页 -->
      <el-tabs v-model="activeTab">
        <el-tab-pane label="聚类分布" name="distribution">
          <div class="distribution-header mb-3" style="display: flex; justify-content: flex-end;">
            <el-button type="text" size="small" @click="showClusterCenterDetails = !showClusterCenterDetails">
              {{ showClusterCenterDetails ? '收起聚类中心详情' : '查看聚类中心详情' }}
            </el-button>
          </div>
          <el-table :data="clusterResult.cluster_distribution" style="width: 100%">
            <el-table-column prop="cluster_id" label="聚类ID" width="100" align="center" />
            <el-table-column prop="cluster_name" label="聚类名称" width="150" />
            <el-table-column prop="size" label="样本数量" width="120" align="center" />
            <el-table-column prop="percentage" label="百分比" width="120" align="center">
              <template #default="scope">{{ scope.row.percentage.toFixed(2) }}%</template>
            </el-table-column>
            <el-table-column label="聚类特点" min-width="260">
              <template #default="scope">
                <div class="cluster-summary">
                  <div class="summary-text">{{ scope.row.summary || '—' }}</div>
                  <div class="top-features" v-if="Array.isArray(scope.row.top_features) && scope.row.top_features.length">
                    <el-tag
                      v-for="feat in scope.row.top_features"
                      :key="feat.feature"
                      size="small"
                      class="feature-chip"
                      type="info"
                    >
                      {{ formatTopFeature(feat) }}
                    </el-tag>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="聚类中心">
              <template #default="scope">
                <div class="center-display">
                  <span
                    v-for="([key, value], index) in getCenterEntries(scope.row.center)"
                    :key="key"
                    class="center-item"
                  >
                    {{ key }}: {{ typeof value === 'number' ? value.toFixed(2) : value }}
                  </span>
                  <span
                    v-if="!showClusterCenterDetails && scope.row.center && Object.keys(scope.row.center).length > centerPreviewCount"
                    class="center-item"
                  >
                    ...
                  </span>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        
        <el-tab-pane label="可视化" name="visualization">
          <div class="visualization-container">
            <div class="vis-controls mb-3">
              <el-form :inline="true" class="vis-controls-form">
                <el-form-item class="chart-type-item">
                  <template #label>
                    <span class="chart-type-label">图表类型</span>
                  </template>
                  <div class="select-with-hint">
                    <el-select
                      v-model="visualizationType"
                      class="chart-type-select"
                      @change="updateVisualization"
                      :popper-class="'chart-type-select-popper'"
                    >
                      <el-option label="地图" value="map" />
                      <el-option label="饼图" value="pie" />
                      <el-option label="柱状图" value="bar" />
                    </el-select>
                  </div>
                </el-form-item>
                <el-form-item
                  v-if="visualizationType === 'map'"
                  class="cluster-toggle-item"
                >
                  <template #label>
                    <span class="chart-type-label">显示聚类</span>
                  </template>
                  <el-switch
                    v-model="showClusterOnMap"
                    size="small"
                    @change="updateVisualization"
                  />
                </el-form-item>
              </el-form>
            </div>
            <div class="visualization-main">
              <div
                v-if="visualizationType === 'map' && clusterResult && clusterLegendItems && clusterLegendItems.length"
                class="cluster-legend-column"
              >
                <div class="cluster-legend-panel">
                  <div class="cluster-legend-header">聚类说明</div>
                  <div
                    v-for="item in clusterLegendItems"
                    :key="item.id"
                    class="cluster-legend-item"
                  >
                    <div class="cluster-legend-switch">
                      <span
                        class="cluster-color-dot"
                        :style="{ backgroundColor: clusterColorMap[item.id] || '#9CA3AF' }"
                      ></span>
                      <el-switch
                        v-model="clusterVisibility[item.id]"
                        size="small"
                        @change="updateVisualization"
                      />
                    </div>
                    <div class="cluster-legend-text">
                      <div class="cluster-legend-name">{{ item.name }}</div>
                      <div class="cluster-legend-desc">{{ item.description }}</div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="chart-wrapper">
                <div ref="chartContainer" class="chart-container"></div>
              </div>
            </div>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="时间走势" name="timeTrend" v-if="hasTimeTrends">
          <div class="time-trend-panel">
            <div class="trend-chart" ref="trendChartRef" style="width: 100%; height: 360px;"></div>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="评估指标" name="metrics">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="算法">{{ clusterResult.algorithm.toUpperCase() }}</el-descriptions-item>
            <el-descriptions-item label="聚类数量">{{ clusterResult.n_clusters }}</el-descriptions-item>
            <el-descriptions-item label="轮廓系数">{{ clusterResult.silhouette_score.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="Davies-Bouldin指数">{{ clusterResult.davies_bouldin_score.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="Calinski-Harabasz指数">{{ clusterResult.calinski_harabasz_score.toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="执行时间">{{ clusterResult.execution_time }}秒</el-descriptions-item>
            <el-descriptions-item label="总样本数">{{ clusterResult.total_samples }}</el-descriptions-item>
            <el-descriptions-item label="特征数量">{{ clusterResult.features.length }}</el-descriptions-item>
            <el-descriptions-item label="使用特征" :span="2">{{ clusterResult.features.join(', ') }}</el-descriptions-item>
            <el-descriptions-item label="惯性值" v-if="clusterResult.inertia" :span="2">{{ clusterResult.inertia.toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="噪声点数量" v-if="clusterResult.n_noise !== undefined" :span="2">{{ clusterResult.n_noise }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>
<script>
import api from '@/api'
const { file: fileApi, analysis: analysisApi, template: templateApi } = api
// 使用完整 ECharts 包，避免 cartesian2d 注册问题
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

/**
 * 聚类分析组件
 * 用于配置和执行聚类分析任务，展示聚类结果和可视化图表
 * 支持K-means、层次聚类、GMM等多种聚类算法
 * 提供地图、饼图、柱状图等多种可视化方式
 */
export default {
  name: 'Cluster',
  components: {},
  data() {
    return {
      selectedFileId: '',
      availableFiles: [],
      fileInfo: null,
      availableFeatures: [],
      dataTypes: {},
      clusterConfig: {
        algorithm: 'kmeans',
        features: [],
        nClusters: 3,
        maxIter: 300,
        linkage: 'ward',
        covarianceType: 'full',
        randomState: 42,
        standardize: false,
        dimensionalityReduction: 'none',
        pcaComponents: 20
      },
      activeCollapseNames: [],
      isAllFeaturesSelected: false,
      isClustering: false,
      isEstimatingK: false,
      showKEstimation: false,
      kEstimationData: null,
      hasResults: false,
      clusterResult: null,
      activeTab: 'distribution',
      visualizationType: 'map',
      chartInstance: null,
      geojsonFiles: [],
      selectedGeojsonId: '',
      isLoadingGeojson: false,
      showClusterCenterDetails: false,
      centerPreviewCount: 3,
      showClusterOnMap: true,
      clusterVisibility: {},
      clusterLegendItems: [],
      clusterColorMap: {},
      trendChartInstance: null,
      // 历史模板数据
      historyTemplates: [],
      // 模板搜索关键字
      templateSearchKeyword: '',
      // 模板排序配置
      templateSort: {
        prop: 'createdAt',
        order: 'descending' // 默认按创建时间倒序
      },
      // 是否正在使用模板
      isUsingTemplate: false,
      // 地区搜索关键字（用于地区选择的搜索框）
      featureSearchKeyword: ''
    }
  },
  computed: {
    // 地区搜索过滤结果：基于 availableFeatures 和 featureSearchKeyword
    filteredFeatures() {
      const cols = this.availableFeatures || []
      const kw = (this.featureSearchKeyword || '').trim().toLowerCase()
      if (!kw) return cols
      return cols.filter(name => String(name).toLowerCase().includes(kw))
    },
    // 当前搜索结果中的已选地区（用于 tag 展示），顺序与上方复选框一致
    displayedClusterTags() {
      const selectedSet = new Set(this.clusterConfig.features || [])
      const kw = (this.featureSearchKeyword || '').trim().toLowerCase()
      if (!kw) {
        const all = this.availableFeatures || []
        return all.filter(f => selectedSet.has(f))
      }
      const visible = this.filteredFeatures || []
      return visible.filter(f => selectedSet.has(f))
    },
    // 过滤和排序后的模板列表
    filteredTemplates() {
      let templates = [...this.historyTemplates]
      
      // 按名称搜索
      if (this.templateSearchKeyword) {
        const keyword = this.templateSearchKeyword.trim().toLowerCase()
        templates = templates.filter(template => 
          template.name.toLowerCase().includes(keyword)
        )
      }
      
      // 排序
      if (this.templateSort.prop && this.templateSort.order) {
        const { prop, order } = this.templateSort
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
    },
    canEstimateK() {
      return this.selectedFileId && this.clusterConfig.features && this.clusterConfig.features.length > 0
    },
    // 是否可以运行聚类（用于控制保存模板按钮）
    canRunCluster() {
      return this.selectedFileId && this.clusterConfig.features && this.clusterConfig.features.length > 0
    },
    visualizationLabel() {
      const map = { map: '地图', pie: '饼图', bar: '柱状图' }
      return map[this.visualizationType] || '未选择'
    },
    hasTimeTrends() {
      return this.clusterResult && Array.isArray(this.clusterResult.time_trends) && this.clusterResult.time_trends.length > 0
    }
  },
  mounted() {
    this.loadAvailableFiles()
    this.loadHistoryTemplates()
  },
  beforeUnmount() {
    if (this.chartInstance) {
      this.chartInstance.dispose()
    }
    if (this.trendChartInstance) {
      this.trendChartInstance.dispose()
    }
  },
  watch: {
    activeTab(newVal) {
      if (newVal === 'visualization' && this.hasResults) {
        this.$nextTick(() => {
          this.initChart()
        })
      }
      if (newVal === 'timeTrend' && this.hasTimeTrends) {
        this.$nextTick(() => {
          this.initTrendChart()
        })
      }
    },
    'clusterResult.time_trends'(newTrends) {
      if (newTrends && newTrends.length && this.activeTab === 'timeTrend') {
        this.$nextTick(() => this.initTrendChart())
      }
    }
  },
  methods: {
    async loadAvailableFiles() {
      try {
        const response = await fileApi.getFileList(1, 100)
        if (response.success) {
          this.availableFiles = response.data.files || []
        }
      } catch (error) {
        this.$message.error('加载文件列表失败')
        console.error(error)
      }
    },
    formatTopFeature(feat) {
      if (!feat || !feat.feature) return ''
      const delta = typeof feat.delta === 'number' ? feat.delta : 0
      const direction = delta >= 0 ? '高于' : '低于'
      return `${feat.feature} ${direction}${Math.abs(delta).toFixed(2)}`
    },
    async loadFileInfo() {
      if (!this.selectedFileId) {
        this.$message.warning('请先选择文件')
        return
      }
      try {
        const response = await fileApi.previewFile(this.selectedFileId, 1, 5)
        if (response.success) {
          this.fileInfo = {
            ...response.data.file_info,
            row_count: response.data.total_rows,
            column_count: response.data.columns?.length || 0,
            columns: response.data.columns || []
          }
          try {
            const info = await fileApi.getFileInfo(this.selectedFileId)
            if (info.success && info.data && info.data.data_types) {
              this.dataTypes = info.data.data_types
            } else {
              this.dataTypes = {}
            }
          } catch (_) {
            this.dataTypes = {}
          }
          // 仅保留数值列供“地区选择”使用，界面中不显示无法参与聚类的列
          const allCols = response.data.columns || []
          const numeric = allCols.filter(f => this.isNumericType(this.dataTypes?.[f]))
          this.availableFeatures = numeric
          // 只有在没有从模板加载结果时，才重置特征选择和结果
          if (!this.hasResults) {
            this.clusterConfig.features = numeric
            this.isAllFeaturesSelected = numeric.length > 0
            this.showKEstimation = false
          }
          this.$message.success('文件信息加载成功')
          // 同时尝试加载可用的 GeoJSON/JSON 地图文件列表，使用await确保执行完成
          // 传递autoSelect=false，避免覆盖已经设置的地图文件ID
          await this.loadGeojsonFiles(false)
        }
      } catch (error) {
        this.$message.error('加载文件信息失败')
        console.error(error)
      }
    },
    async loadGeojsonFiles(autoSelect = true) {
      this.isLoadingGeojson = true
      try {
        const resp = await fileApi.getFileList(1, 100)
        if (resp.success && resp.data && Array.isArray(resp.data.files)) {
          const files = (resp.data.files || []).filter(f => {
            const ext = String(f.extension || '').toLowerCase()
            return ext === 'geojson' || ext === 'json'
          })
          this.geojsonFiles = files
          if (!files.length) {
            this.$message.warning('未找到 GeoJSON/JSON 地图文件，请在数据管理中上传')
          } else if (autoSelect && (!this.selectedGeojsonId || !files.some(f => f.id === this.selectedGeojsonId))) {
            this.selectedGeojsonId = files[0].id
          }
        }
      } catch (error) {
        this.$message.error('加载地图文件失败')
        console.error(error)
      } finally {
        this.isLoadingGeojson = false
      }
    },
    isNumericType(t) {
      const s = String(t || '').toLowerCase()
      return s.includes('int') || s.includes('float') || s.includes('double') || s.includes('number')
    },
    handleFeaturesSelectAll(checked) {
      const visible = this.filteredFeatures
      if (!visible || visible.length === 0) {
        this.isAllFeaturesSelected = false
        return
      }

      const current = new Set(this.clusterConfig.features || [])
      if (checked) {
        // 只对当前搜索结果中的数值列执行全选
        visible.forEach(f => {
          if (this.isNumericType(this.dataTypes?.[f])) current.add(f)
        })
      } else {
        // 只对当前搜索结果中的列取消选择
        const visibleSet = new Set(visible)
        for (const f of visibleSet) {
          current.delete(f)
        }
      }
      this.clusterConfig.features = Array.from(current)

      const selectedSet = new Set(this.clusterConfig.features || [])
      this.isAllFeaturesSelected = visible.every(f => selectedSet.has(f))
    },
    handleFeaturesSelect() {
      // 当特征选择变化时，基于当前过滤结果重新计算全选状态
      const visible = this.filteredFeatures
      if (!visible || visible.length === 0) {
        this.isAllFeaturesSelected = false
        return
      }
      const selectedSet = new Set(this.clusterConfig.features || [])
      this.isAllFeaturesSelected = visible.every(feature => selectedSet.has(feature))
    },
    removeFeature(feature) {
      const index = this.clusterConfig.features.indexOf(feature)
      if (index > -1) {
        this.clusterConfig.features.splice(index, 1)
      }
      // 删除 tag 后同步更新全选状态
      this.handleFeaturesSelect()
    },
    async runClustering() {
      if (!this.selectedFileId) {
        this.$message.error('请选择数据文件')
        return
      }
      if (!this.clusterConfig.features || this.clusterConfig.features.length === 0) {
        this.$message.error('请至少选择一个特征')
        return
      }
      const numericSelected = (this.clusterConfig.features || []).filter(f => this.isNumericType(this.dataTypes?.[f]))
      if (numericSelected.length !== this.clusterConfig.features.length) {
        this.$message.warning('已自动移除非数值列，仅对数值列进行聚类')
        this.clusterConfig.features = numericSelected
      }
      if (this.clusterConfig.features.length === 0) {
        this.$message.error('所选特征均为非数值列，无法进行聚类')
        return
      }
      if ((this.clusterConfig.algorithm === 'kmeans' || this.clusterConfig.algorithm === 'gmm' || this.clusterConfig.algorithm === 'hierarchical') && !this.clusterConfig.nClusters) {
        this.$message.error('请输入聚类数量')
        return
      }
      // 样本数量校验：至少要满足 n_samples >= n_clusters，避免后端 400 错误
      const totalRows = this.fileInfo?.row_count || 0
      if (totalRows > 0 && totalRows < this.clusterConfig.nClusters) {
        this.$message.error(`当前可用样本数为 ${totalRows}，需要大于等于聚类数量 ${this.clusterConfig.nClusters}`)
        return
      }
      this.isClustering = true
      this.hasResults = false
      try {
        const params = {
          file_id: this.selectedFileId,
          algorithm: this.clusterConfig.algorithm,
          features: this.clusterConfig.features,
          n_clusters: this.clusterConfig.nClusters,
          max_iter: this.clusterConfig.maxIter,
          linkage: this.clusterConfig.linkage,
          covariance_type: this.clusterConfig.covarianceType,
          random_state: this.clusterConfig.randomState,
          standardize: this.clusterConfig.standardize,
          dimensionality_reduction: this.clusterConfig.dimensionalityReduction,
          pca_components: this.clusterConfig.pcaComponents
        }
        const response = await analysisApi.clusterAnalysis(params)
        if (response.success) {
          this.clusterResult = response.data
          this.hasResults = true
          // 如果是按地区聚类，将结果写入全局以供地图页面使用
          window.__lastClusterResult = {
            mode: 'region',
            file_id: this.selectedFileId,
            data: this.clusterResult
          }
          if (this.activeTab === 'visualization') {
            this.$nextTick(() => this.initChart())
          }
          if (this.activeTab === 'timeTrend') {
            this.$nextTick(() => this.initTrendChart())
          }
          this.$message.success('聚类分析完成')
        } else {
          this.$message.error(response.message || '聚类分析失败')
        }
      } catch (error) {
        this.$message.error(error.message || '聚类分析失败')
        console.error(error)
      } finally {
        this.isClustering = false
      }
    },
    async estimateK() {
      if (!this.canEstimateK) {
        this.$message.warning('请先选择文件和特征')
        return
      }
      this.isEstimatingK = true
      this.showKEstimation = false
      try {
        const params = {
          file_id: this.selectedFileId,
          features: this.clusterConfig.features,
          k_min: 2,
          k_max: 10,
          standardize: this.clusterConfig.standardize
        }
        const response = await analysisApi.estimateOptimalK(params)
        if (response.success) {
          this.kEstimationData = response.data
          this.showKEstimation = true
          this.clusterConfig.nClusters = response.data.recommended_k
          this.$message.success(`K值估计完成，推荐K=${response.data.recommended_k}`)
        } else {
          this.$message.error(response.message || 'K值估计失败')
        }
      } catch (error) {
        this.$message.error(error.message || 'K值估计失败')
        console.error(error)
      } finally {
        this.isEstimatingK = false
      }
    },
    resetConfig() {
      // 重置为初始状态：清空文件选择、重置配置、清空结果
      this.selectedFileId = ''
      this.fileInfo = null
      this.clusterConfig = {
        algorithm: 'kmeans',
        features: [],
        nClusters: 3,
        maxIter: 300,
        linkage: 'ward',
        covarianceType: 'full',
        randomState: 42,
        standardize: false,
        dimensionalityReduction: 'none',
        pcaComponents: 2
      }
      this.isAllFeaturesSelected = false
      this.hasResults = false
      this.clusterResult = null
      this.showKEstimation = false
      this.showClusterCenterDetails = false
      this.$message.success('配置已重置')
    },
    initChart() {
      this.$nextTick(() => {
        const el = this.$refs.chartContainer
        if (!el) return
        const { clientWidth, clientHeight } = el
        if (!clientWidth || !clientHeight) {
          // 容器尚未完成布局，等下次可视化交互时再初始化，避免 ECharts 报宽高为 0
          return
        }
        if (this.chartInstance) {
          this.chartInstance.dispose()
        }
        this.chartInstance = echarts.init(el)
        this.updateVisualization()
      })
    },
    updateVisualization() {
      if (!this.clusterResult) return
      this.$nextTick(() => {
        const el = this.$refs.chartContainer
        if (!el) return
        const { clientWidth, clientHeight } = el
        if (!clientWidth || !clientHeight) {
          // 容器宽高为 0 时不初始化，避免 ECharts 报错
          return
        }
        if (this.chartInstance) {
          this.chartInstance.dispose()
        }
        this.chartInstance = echarts.init(el)
        if (this.visualizationType === 'map') {
          this.renderMapChart()
        } else if (this.visualizationType === 'pie') {
          this.renderPieChart()
        } else if (this.visualizationType === 'bar') {
          this.renderBarChart()
        }
      })
    },
    initTrendChart() {
      this.$nextTick(() => {
        const el = this.$refs.trendChartRef
        if (!el || !this.hasTimeTrends) return
        const { clientWidth, clientHeight } = el
        if (!clientWidth || !clientHeight) {
          setTimeout(() => {
            if (this.activeTab === 'timeTrend' && this.hasTimeTrends) {
              this.initTrendChart()
            }
          }, 120)
          return
        }
        if (this.trendChartInstance) {
          this.trendChartInstance.dispose()
        }
        this.trendChartInstance = echarts.init(el)
        this.renderTrendChart()
      })
    },
    renderTrendChart() {
      if (!this.trendChartInstance || !this.hasTimeTrends) return
      const trends = this.clusterResult.time_trends || []

      const palette = ['#4F46E5', '#22C55E', '#F97316', '#EC4899', '#0EA5E9']

      const series = trends.map((trend, idx) => ({
        name: `簇 ${trend.cluster_id}`,
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: {
          width: 2
        },
        itemStyle: {
          color: palette[idx % palette.length]
        },
        areaStyle: {
          opacity: 0
        },
        data: (trend.points || []).map(p => [p.timestamp, p.value])
      }))

      const option = {
        backgroundColor: '#FFFFFF',
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            // 显式关闭轴指示器，避免出现竖线
            type: 'none'
          },
          formatter: params => {
            if (!params || !params.length) return ''
            const t = params[0].axisValueLabel
            const lines = params.map(p => `${p.marker} ${p.seriesName}: ${p.data[1].toFixed(3)}`)
            return [t].concat(lines).join('<br/>')
          }
        },
        legend: {
          top: 8,
          left: 'center',
          icon: 'circle',
          textStyle: {
            color: '#4B5563',
            fontSize: 12
          }
        },
        grid: { left: 56, right: 24, top: 48, bottom: 40 },
        xAxis: {
          type: 'time',
          boundaryGap: false,
          axisLine: { lineStyle: { color: '#D1D5DB' } },
          axisTick: { show: false },
          axisLabel: {
            color: '#6B7280',
            fontSize: 11
          },
          splitLine: {
            show: false
          }
        },
        yAxis: {
          type: 'value',
          name: '平均值',
          nameTextStyle: {
            color: '#4B5563',
            fontSize: 12,
            padding: [0, 0, 4, 0]
          },
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: {
            color: '#6B7280',
            fontSize: 11
          },
          splitLine: {
            show: true,
            lineStyle: {
              color: '#E5E7EB',
              type: 'dashed'
            }
          }
        },
        series
      }

      this.trendChartInstance.setOption(option)
    },
    formatTimeLabel(value) {
      if (!value) return ''
      const d = new Date(value)
      if (isNaN(d.getTime())) return String(value)
      return d.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    },
    normalizeName(value) {
      if (value === null || value === undefined) return ''
      let s = String(value)
      // 尽量去除重音/变音符号，增强不同来源名称的一致性
      try {
        if (s.normalize) {
          s = s.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        }
      } catch (_) {
        // 某些旧环境可能不支持 normalize，忽略即可
      }
      return s
        .trim()
        .toLowerCase()
        // 将下划线、连字符等统一视为空格
        .replace(/[\-_]+/g, ' ')
        // 去掉括号及括号内内容
        .replace(/\([^)]*\)/g, '')
        // 只保留字母数字和空格
        .replace(/[^a-z0-9\s]/g, '')
        // 合并多余空格
        .replace(/\s+/g, ' ')
    },
    getCenterEntries(center) {
      if (!center) return []
      const entries = Object.entries(center)
      if (this.showClusterCenterDetails) return entries
      return entries.slice(0, this.centerPreviewCount)
    },
    async renderMapChart() {
      if (!this.clusterResult) {
        this.$message.warning('请先执行聚类分析')
        return
      }
      if (!this.selectedGeojsonId) {
        this.$message.warning('请先选择地图 GeoJSON 文件')
        return
      }
      if (!this.$refs.chartContainer || !this.chartInstance) return
      try {
        const resp = await fileApi.getFileContent(this.selectedGeojsonId)
        if (!resp || !resp.success) {
          this.$message.error(resp?.message || '加载 GeoJSON 失败')
          return
        }
        const raw = resp.data
        let geojson
        try {
          geojson = typeof raw === 'string' ? JSON.parse(raw) : raw
        } catch (e) {
          console.error(e)
          this.$message.error('解析 GeoJSON 失败')
          return
        }
        const res = this.clusterResult
        if (!Array.isArray(res.labels) || !Array.isArray(res.objects)) {
          this.$message.error('聚类结果缺少地区标签信息')
          return
        }
        const visibility = this.clusterVisibility || {}
        const regionToCluster = {}
        res.objects.forEach((name, idx) => {
          const key = this.normalizeName(name)
          const raw = res.labels[idx]
          const cluster = Number.isFinite(raw) && raw >= 0 ? raw : -1
          regionToCluster[key] = cluster
        })
        const features = geojson.features || []
        const showCluster = this.showClusterOnMap
        const data = features.map(f => {
          const props = f.properties || {}
          const name = props.NAME_3 || props.NAME_2 || props.NAME || props.NIL || props.name
          // 将选择出的名称写回到 GeoJSON 的统一 name 字段，便于 ECharts 按名称匹配
          props.name = name
          const key = this.normalizeName(name)
          const rawCluster = regionToCluster[key]
          const cluster = Number.isFinite(rawCluster) && rawCluster >= 0 ? rawCluster : -1
          const visible = showCluster && !(Number.isFinite(cluster) && cluster >= 0 && visibility[cluster] === false)
          return {
            name,
            // 关闭聚类显示或该簇未选中时，将值设为 -1，使其走 outOfRange 的统一灰色
            value: visible ? cluster : -1,
            // showCluster 关闭或该簇未选中时，不在 tooltip 中使用 clusterId
            clusterId: visible && Number.isFinite(rawCluster) && rawCluster >= 0 ? rawCluster : null
          }
        })
        const validLabels = Array.isArray(res.labels)
          ? res.labels.filter(v => Number.isFinite(v) && v >= 0)
          : []
        const maxCluster = validLabels.length ? Math.max(...validLabels) : 0
        const palette = ['#4F46E5', '#22C55E', '#F97316', '#EF4444', '#0EA5E9', '#A855F7', '#EAB308', '#22C55E']

        // 构建“聚类ID -> 地区列表”映射，用于 tooltip 展示代表地区
        const clusterMembersMap = {}
        if (Array.isArray(res.labels) && Array.isArray(res.objects)) {
          res.labels.forEach((label, idx) => {
            if (!Number.isFinite(label) || label < 0) return
            const regionName = res.objects[idx]
            const key = String(label)
            if (!clusterMembersMap[key]) clusterMembersMap[key] = []
            clusterMembersMap[key].push(regionName)
          })
        }

        // 计算全局中心均值，用于粗略判断“整体水平”高/低
        let globalCenterMean = null
        if (Array.isArray(res.cluster_distribution) && res.cluster_distribution.length) {
          const allValues = []
          res.cluster_distribution.forEach(c => {
            if (!c || !c.center) return
            Object.values(c.center).forEach(v => {
              if (typeof v === 'number' && Number.isFinite(v)) {
                allValues.push(v)
              }
            })
          })
          if (allValues.length) {
            globalCenterMean = allValues.reduce((sum, v) => sum + v, 0) / allValues.length
          }
        }

        // 为每个聚类构建摘要：代表地区示例 + 更细粒度的整体水平描述
        const clusterSummaryMap = {}
        if (Array.isArray(res.cluster_distribution)) {
          res.cluster_distribution.forEach(c => {
            const cid = c.cluster_id
            if (!Number.isFinite(cid) || cid < 0) return
            const center = c.center || {}
            const values = Object.values(center).filter(v => typeof v === 'number' && Number.isFinite(v))
            const mean = values.length ? values.reduce((sum, v) => sum + v, 0) / values.length : null
            let levelText = ''
            if (globalCenterMean != null && mean != null && globalCenterMean > 0) {
              const ratio = mean / globalCenterMean
              const ratioText = `（约为全局的 ${ratio.toFixed(2)} 倍）`
              if (ratio >= 1.5) {
                levelText = `整体水平：显著高于全局平均${ratioText}`
              } else if (ratio >= 1.2) {
                levelText = `整体水平：明显高于全局平均${ratioText}`
              } else if (ratio >= 1.05) {
                levelText = `整体水平：略高于全局平均${ratioText}`
              } else if (ratio <= 0.67) {
                levelText = `整体水平：显著低于全局平均${ratioText}`
              } else if (ratio <= 0.83) {
                levelText = `整体水平：明显低于全局平均${ratioText}`
              } else if (ratio <= 0.95) {
                levelText = `整体水平：略低于全局平均${ratioText}`
              } else {
                levelText = `整体水平：接近全局平均${ratioText}`
              }
            }
            const members = clusterMembersMap[String(cid)] || []
            const examples = members.slice(0, 3)
            clusterSummaryMap[cid] = {
              levelText,
              examples
            }
          })
        }

        // 基于聚类分布构建颜色映射、legend 项，以及 visualMap 的 pieces
        const colorMap = {}
        const legendItems = []
        const clusterPieces = Array.isArray(res.cluster_distribution)
          ? res.cluster_distribution
              .filter(c => Number.isFinite(c.cluster_id) && c.cluster_id >= 0)
              .map((c, idx) => {
                const cid = c.cluster_id
                const color = palette[idx % palette.length]
                colorMap[cid] = color

                const summary = clusterSummaryMap[cid] || {}
                const examplesText = Array.isArray(summary.examples) && summary.examples.length
                  ? `代表地区：${summary.examples.join('，')}`
                  : ''
                const levelText = summary.levelText || ''
                let description = ''
                if (levelText && examplesText) {
                  description = `${levelText}；${examplesText}`
                } else if (levelText) {
                  description = levelText
                } else if (examplesText) {
                  description = examplesText
                } else {
                  description = '该聚类在所选指标上的模式相似。'
                }

                legendItems.push({
                  id: cid,
                  name: c.cluster_name || `聚类 ${cid}`,
                  description
                })

                // 默认所有簇可见（如果还未初始化）
                if (typeof this.clusterVisibility[cid] === 'undefined') {
                  this.clusterVisibility[cid] = true
                }

                return {
                  value: cid,
                  label: c.cluster_name || `聚类 ${cid}`,
                  color
                }
              })
          : []

        this.clusterLegendItems = legendItems
        this.clusterColorMap = colorMap

        const option = {
          backgroundColor: '#F9FAFB',
          animation: false,
          tooltip: {
            trigger: 'item',
            formatter: params => {
              const name = params.name || '未知地区'
              // 关闭聚类显示或该簇被隐藏时，只展示地区名称
              if (!showCluster) {
                return name
              }
              const rawFromData = params.data && typeof params.data.clusterId === 'number' ? params.data.clusterId : null
              const fromValue = typeof params.value === 'number' ? params.value : null
              const cluster = Number.isFinite(rawFromData) && rawFromData >= 0
                ? rawFromData
                : (Number.isFinite(fromValue) && fromValue >= 0 ? fromValue : -1)
              if (!Number.isFinite(cluster) || cluster < 0) {
                return `${name}<br/>未在本次聚类中匹配`
              }
              if (visibility[cluster] === false) {
                return name
              }
              let extra = ''
              if (Array.isArray(res.cluster_distribution)) {
                const info = res.cluster_distribution.find(c => c.cluster_id === cluster)
                if (info) {
                  extra = `<br/>聚类名称：${info.cluster_name}<br/>样本数：${info.size}`
                }
              }
              const summary = clusterSummaryMap[cluster]
              let examplesPart = ''
              let levelPart = ''
              if (summary) {
                if (Array.isArray(summary.examples) && summary.examples.length) {
                  const names = summary.examples.join('，')
                  examplesPart = `<br/>代表地区示例：${names}`
                }
                if (summary.levelText) {
                  levelPart = `<br/>${summary.levelText}`
                }
              }
              return `${name}<br/>所属聚类：${cluster}${extra}${examplesPart}${levelPart}`
            }
          },
          visualMap: {
            show: false,
            type: 'piecewise',
            min: 0,
            max: maxCluster,
            orient: 'vertical',
            left: 10,
            bottom: 20,
            text: ['聚类', ''],
            textStyle: { fontSize: 12 },
            itemWidth: 14,
            itemHeight: 14,
            inRange: {
              color: palette
            },
            outOfRange: {
              color: '#E5E7EB'
            },
            hoverLink: true,
            selectedMode: 'multiple',
            pieces: clusterPieces
          },
          series: [
            {
              name: '聚类结果',
              type: 'map',
              map: 'cluster-geo',
              roam: true,
              zoom: 1,
              scaleLimit: {
                min: 0.8,
                max: 5
              },
              label: {
                show: false,
                color: '#111827',
                fontSize: 10
              },
              itemStyle: {
                borderColor: '#FFFFFF',
                borderWidth: 0.5
              },
              emphasis: {
                label: { show: true },
                itemStyle: {
                  borderColor: '#111827',
                  borderWidth: 1,
                  shadowBlur: 8,
                  shadowColor: 'rgba(15, 23, 42, 0.35)'
                }
              },
              data
            }
          ]
        }
        echarts.registerMap('cluster-geo', geojson)
        this.chartInstance.setOption(option)
      } catch (error) {
        console.error(error)
        this.$message.error(error.message || '地图渲染失败')
      }
    },
    renderPieChart() {
      const data = this.clusterResult.cluster_distribution.map(cluster => ({
        name: cluster.cluster_name,
        value: cluster.size
      }))
      
      const option = {
        title: { text: '聚类分布饼图', left: 'center' },
        tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
        legend: { bottom: 10 },
        series: [{
          type: 'pie',
          radius: '60%',
          data: data,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }]
      }
      this.chartInstance.setOption(option, true)
    },
    renderBarChart() {
      const xData = this.clusterResult.cluster_distribution.map(c => c.cluster_name)
      const yData = this.clusterResult.cluster_distribution.map(c => c.size)
      const total = this.clusterResult.total_samples || yData.reduce((a,b)=>a+b,0)
      const fmtCount = this.formatCount
      
      const option = {
        title: { text: '聚类样本数量', left: 'center' },
        tooltip: {
          show: false
        },
        xAxis: { type: 'category', data: xData },
        yAxis: { type: 'value', name: '样本数量' },
        series: [{
          type: 'bar',
          data: yData,
          itemStyle: { color: 'var(--primary-color)' },
          emphasis: { disabled: true },
          label: {
            show: true,
            position: 'top',
            formatter: (p) => {
              const count = p.data
              const pct = total ? (count / total * 100).toFixed(1) : '0.0'
              return `${fmtCount(count)} (${pct}%)`
            },
            color: '#606266',
            fontSize: 11
          }
        }]
      }
      this.chartInstance.setOption(option)
    },
    formatFileSize(bytes) {
      if (!bytes) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    },
    formatDateTime(dateTimeStr) {
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
    },
    // Number formatting helpers
    formatCount(n) {
      const num = Number(n) || 0
      return num.toLocaleString('en-US')
    },
    // 加载历史模板
    async loadHistoryTemplates() {
      try {
        const response = await templateApi.getTemplates('cluster')
        this.historyTemplates = response.data || []
      } catch (error) {
        console.error('加载模板失败:', error)
        this.historyTemplates = []
        ElMessage.error('加载模板失败: ' + (error.message || '未知错误'))
      }
    },
    // 保存为模板
    async saveAsTemplate() {
      let templateName = prompt('请输入模板名称：')
      if (!templateName) return
      
      templateName = templateName.trim()
      if (!templateName) return
      
      // 检查模板名称是否已存在
      await this.loadHistoryTemplates()
      const isDuplicate = this.historyTemplates.some(t => t.name === templateName)
      if (isDuplicate) {
        this.$message.error('模板名称已存在，请更改模板名称')
        return
      }
      
      console.log('开始保存模板，模板名称:', templateName)
      
      // 创建模板对象，保存完整的模板内容
      const templateData = {
        name: templateName,
        type: 'cluster',
        config: {
          algorithm: this.clusterConfig.algorithm,
          features: [...this.clusterConfig.features],
          nClusters: this.clusterConfig.nClusters,
          maxIter: this.clusterConfig.maxIter,
          linkage: this.clusterConfig.linkage,
          covarianceType: this.clusterConfig.covarianceType,
          randomState: this.clusterConfig.randomState,
          standardize: this.clusterConfig.standardize,
          dimensionalityReduction: this.clusterConfig.dimensionalityReduction,
          pcaComponents: this.clusterConfig.pcaComponents,
          fileId: this.selectedFileId
        },
        results: {
          // 只保存必要的结果信息，不保存完整的聚类结果
          hasResults: this.hasResults,
          activeTab: this.activeTab,
          visualizationType: this.visualizationType,
          showClusterOnMap: this.showClusterOnMap,
          // 保存模板创建时的原文件ID和名称，用于加载时检查
          originalFile: {
            id: this.selectedFileId,
            name: this.fileInfo?.original_filename || this.selectedFileId
          },
          // 保存模板创建时的地图文件名，用于加载时根据名称选择
          geojsonFileName: this.geojsonFiles.find(f => f.id === this.selectedGeojsonId)?.original_filename || ''
        }
      }
      
      try {
        console.log('模板数据构建完成，开始计算数据大小...')
        const dataSize = JSON.stringify(templateData).length
        console.log('模板数据大小:', (dataSize / 1024 / 1024).toFixed(2), 'MB')
        
        console.log('开始发送API请求...')
        const startTime = Date.now()
        
        // 保存到后端API
        const response = await templateApi.createTemplate(templateData)
        
        const endTime = Date.now()
        console.log('API请求完成，耗时:', (endTime - startTime) / 1000, '秒')
        console.log('API响应:', response)
        
        this.$message.success('模板保存成功，包含完整分析结果')
        // 重新加载模板列表
        this.loadHistoryTemplates()
      } catch (error) {
        console.error('保存模板失败:', error)
        console.error('错误详情:', error.response || error.message || error)
        this.$message.error('保存模板失败：' + (error.message || '未知错误'))
      }
    },
    // 加载模板
    async loadTemplate(template) {
      if (!template) return
      
      // 加载模板配置
      this.clusterConfig = {
        algorithm: template.config.algorithm,
        features: [...template.config.features],
        nClusters: template.config.nClusters,
        maxIter: template.config.maxIter,
        linkage: template.config.linkage,
        covarianceType: template.config.covarianceType,
        randomState: template.config.randomState,
        standardize: template.config.standardize,
        dimensionalityReduction: template.config.dimensionalityReduction,
        pcaComponents: template.config.pcaComponents
      }
      
      // 检查模板创建时的原文件是否存在
      const originalFile = template.results?.originalFile
      if (originalFile) {
        try {
          // 先设置文件ID
          this.selectedFileId = originalFile.id
          
          // 尝试加载文件信息，这会调用loadGeojsonFiles
          await this.loadFileInfo(this.selectedFileId)
          // 设置使用模板标志，禁用地区选择
          this.isUsingTemplate = true
          
          // 从模板中获取地图文件名
          const templateGeojsonName = template.results.geojsonFileName
          
          if (templateGeojsonName) {
            // 在当前地图文件列表中查找对应的地图文件
            const matchingGeojson = this.geojsonFiles.find(f => f.original_filename === templateGeojsonName)
            if (matchingGeojson) {
              // 如果找到，使用它
              this.selectedGeojsonId = matchingGeojson.id
            } else if (this.geojsonFiles.length > 0) {
              // 如果没有找到，使用当前列表中的第一个地图文件
              this.selectedGeojsonId = this.geojsonFiles[0].id
            } else {
              // 如果没有地图文件，清空选择
              this.selectedGeojsonId = ''
            }
          } else if (this.geojsonFiles.length > 0) {
            // 如果模板中没有保存地图文件名，使用当前列表中的第一个地图文件
            this.selectedGeojsonId = this.geojsonFiles[0].id
          } else {
            // 如果没有地图文件，清空选择
            this.selectedGeojsonId = ''
          }
        } catch (error) {
          // 原文件不存在，给出明确的提示
          console.error('原文件不存在，无法加载:', error)
          this.$message.error(`原文件 ${originalFile.name} 已被删除，无法加载`)
        }
      } else if (template.config.fileId) {
        // 尝试从配置中获取文件ID
        try {
          // 先设置文件ID
          this.selectedFileId = template.config.fileId
          
          // 尝试加载文件信息，这会调用loadGeojsonFiles
          await this.loadFileInfo(this.selectedFileId)
          this.isUsingTemplate = true
          
          // 从模板中获取地图文件名
          const templateGeojsonName = template.results.geojsonFileName
          
          if (templateGeojsonName) {
            // 在当前地图文件列表中查找对应的地图文件
            const matchingGeojson = this.geojsonFiles.find(f => f.original_filename === templateGeojsonName)
            if (matchingGeojson) {
              // 如果找到，使用它
              this.selectedGeojsonId = matchingGeojson.id
            } else if (this.geojsonFiles.length > 0) {
              // 如果没有找到，使用当前列表中的第一个地图文件
              this.selectedGeojsonId = this.geojsonFiles[0].id
            } else {
              // 如果没有地图文件，清空选择
              this.selectedGeojsonId = ''
            }
          } else if (this.geojsonFiles.length > 0) {
            // 如果模板中没有保存地图文件名，使用当前列表中的第一个地图文件
            this.selectedGeojsonId = this.geojsonFiles[0].id
          } else {
            // 如果没有地图文件，清空选择
            this.selectedGeojsonId = ''
          }
        } catch (error) {
          console.error('加载文件信息失败:', error)
          this.$message.error('无法加载模板对应的文件')
        }
      }
      
      // 重置结果状态
      this.hasResults = false
      this.clusterResult = null
      this.activeTab = 'distribution'
      this.visualizationType = 'map'
      this.showClusterOnMap = true
      this.clusterLegendItems = []
      this.clusterColorMap = {}
      this.clusterVisibility = {}
      
      // 如果模板包含结果数据，直接加载结果，不需要重新计算
      if (template.results && template.results.clusterResult) {
        // 直接加载结果，不需要重新计算
        this.clusterResult = template.results.clusterResult
        this.hasResults = template.results.hasResults
        this.activeTab = template.results.activeTab || 'distribution'
        this.visualizationType = template.results.visualizationType || 'map'
        this.showClusterOnMap = template.results.showClusterOnMap || true
        
        // 初始化聚类图例和颜色映射
        if (this.clusterResult.cluster_distribution) {
          const colorMap = {}
          const legendItems = this.clusterResult.cluster_distribution.map((c, index) => {
            const cid = c.cluster_id
            // 使用固定的颜色数组，确保每次加载颜色一致
            const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1']
            const color = colors[index % colors.length]
            colorMap[cid] = color
            
            // 默认所有簇可见
            if (typeof this.clusterVisibility[cid] === 'undefined') {
              this.clusterVisibility[cid] = true
            }
            
            return {
              id: cid,
              name: c.cluster_name || `聚类 ${cid}`,
              description: c.summary || ''
            }
          })
          
          this.clusterLegendItems = legendItems
          this.clusterColorMap = colorMap
        }
        
        // 刷新图表
        this.$nextTick(() => {
          if (this.activeTab === 'visualization') {
            this.initChart()
          } else if (this.activeTab === 'timeTrend') {
            this.initTrendChart()
          }
        })
        
        this.$message.success('模板加载成功，已显示历史结果')
      } else {
        this.$message.success('模板加载成功，请点击执行按钮进行分析')
      }
    },
    // 删除模板
    async deleteTemplate(templateId) {
      if (!templateId) return
      
      this.$confirm('确定要删除该模板吗？', '删除确认', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          await templateApi.deleteTemplate(templateId)
          this.$message.success('模板删除成功')
          // 重新加载模板列表
          this.loadHistoryTemplates()
        } catch (error) {
          console.error('删除模板失败:', error)
          this.$message.error('删除模板失败，请重试')
        }
      }).catch(() => {
        // 取消删除
      })
    },
    // 处理模板排序
    handleTemplateSort({ field, order }) {
      this.templateSort = { prop: field, order }
    },
    // 编辑模板名称
    async editTemplateName(template) {
      if (!template) return
      
      const newName = prompt('请输入新的模板名称：', template.name)
      if (!newName || newName.trim() === template.name) return
      
      try {
        await templateApi.updateTemplateName(template.id, newName.trim())
        this.$message.success('模板名称修改成功')
        // 重新加载模板列表
        this.loadHistoryTemplates()
      } catch (error) {
        console.error('修改模板名称失败:', error)
        this.$message.error('修改模板名称失败，请重试')
      }
    }
  }
}
</script>
<style scoped>
.cluster-container {
  padding: 20px;
}

.cluster-container h1 {
  font-size: 24px;
  margin-bottom: 30px;
  color: #303133;
  font-weight: 500;
}

.mb-3 {
  margin-bottom: 15px;
}

.card-header {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 模板搜索栏样式 */
.template-search-input {
  width: 240px;
  margin-left: 20px;
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

.vis-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.vis-controls-form {
  display: flex;
  width: 100%;
  justify-content: space-between;
  align-items: center;
}

.chart-type-item {
  margin-bottom: 0;
  display: flex;
  align-items: center;
}

.chart-type-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  letter-spacing: 0.08em;
}

.select-with-hint {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}



.chart-type-select :deep(.el-select__wrapper) {
  border-radius: 999px;
  padding: 2px 14px;
  border-color: var(--primary-color);
  background-color: #ffffff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
  min-width: 110px;
}

.chart-type-select :deep(.el-select__selected-item) {
  font-weight: 500;
  color: var(--text-primary);
}

.chart-type-select :deep(.el-select__caret) {
  color: var(--primary-color);
}

.chart-type-select-popper :deep(.el-select-dropdown__item) {
  padding: 6px 12px;
}

.chart-type-select-popper :deep(.el-select-dropdown__item.selected) {
  background-color: rgba(249, 115, 22, 0.08);
  color: var(--primary-color);
  font-weight: 500;
}

.cluster-toggle-item {
  margin-left: auto;
  margin-bottom: 0;
  display: flex;
  align-items: center;
}

.chart-type-item :deep(.el-form-item__content),
.cluster-toggle-item :deep(.el-form-item__content) {
  display: flex;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.data-source-selector {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  flex-wrap: nowrap;
}

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

.option-content {
  display: flex;
  flex-direction: column;
}

.text-gray-500 {
  color: #606266;
  font-size: 12px;
}

.algorithm-selector {
  padding: 10px 0;
}

.algorithm-option {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.algorithm-name {
  font-weight: 500;
  color: var(--text-primary);
}

.algorithm-desc {
  font-size: 12px;
  color: var(--text-secondary);
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 10px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.feature-selection-area {
  padding: 10px 0;
}

.select-all-container {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.feature-list {
  padding: 8px 12px;
  border: 1px solid #e6f0f6;
  border-radius: 10px;
  margin-bottom: 15px;
  max-height: 200px;
  overflow-y: auto;
  overflow-x: hidden;
  white-space: normal;
  background: var(--page-inner-bg);
}

 .selection-label {
  color: #606266;
  font-size: 13px;
  font-weight: 500;
  margin-right: 8px;
}

/* 聚类分析页面的已选择项目样式 - 添加滑动条 */
.selected-features-display {
  max-height: 120px;
  overflow-y: auto;
}

.results-summary {
  margin-bottom: 20px;
}

.summary-card {
  background: var(--surface-color);
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  transition: all 0.3s;
}

.summary-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.summary-title {
  font-size: 14px;
  color: #606266;
  margin-bottom: 10px;
}

.summary-value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}



.center-display {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.center-item {
  font-size: 12px;
  padding: 2px 8px;
  background: var(--page-inner-bg);
  border-radius: 4px;
}

.visualization-container {
  position: relative;
  padding: 10px 0;
}

.visualization-main {
  display: flex;
  gap: 16px;
  margin-top: 12px;
}

.cluster-legend-column {
  flex: 0 0 280px;
}

.chart-wrapper {
  flex: 1;
  min-width: 0;
}

.vis-controls {
  padding: 10px;
  background: var(--page-inner-bg);
  border-radius: 8px;
}

.chart-container {
  width: 100%;
  height: 500px;
}

/* 美化结果区域的 Tab 栏（聚类分布 / 可视化 / 时间走势 / 评估指标） */
.cluster-container :deep(.el-tabs__header) {
  margin: 0 0 6px 0;
  border-bottom-color: rgba(148, 163, 184, 0.35);
}

.cluster-container :deep(.el-tabs__item) {
  padding: 8px 20px;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.cluster-container :deep(.el-tabs__item.is-active) {
  color: var(--primary-color);
}

.cluster-container :deep(.el-tabs__item:hover) {
  color: var(--primary-dark);
}

.cluster-container :deep(.el-tabs__active-bar) {
  height: 3px;
  border-radius: 999px;
  background-color: var(--primary-color);
}

.cluster-legend-panel {
  max-width: 320px;
  padding: 10px 12px;
  /* 使用主题色的浅色调，和其它模块浅色主色背景保持一致 */
  background: color-mix(in srgb, var(--primary-color) 10%, #ffffff 90%);
  color: var(--text-primary);
  border-radius: 12px;
  box-shadow: none;
  border: none;
}

.cluster-legend-header {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.cluster-legend-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 4px 0;
}

.cluster-legend-switch {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.cluster-color-dot {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  border: 1px solid rgba(31, 41, 55, 0.25);
}

.cluster-legend-text {
  flex: 1;
}

.cluster-legend-name {
  font-weight: 600;
  margin-bottom: 2px;
  color: var(--text-primary);
}

.cluster-legend-desc {
  font-size: 12px;
  color: #4b5563;
}

.current-select-tag {
  margin-left: 10px;
}

.ghost-btn {
  --ghost-color: var(--primary-color);
  color: var(--ghost-color) !important;
  border-color: var(--ghost-color) !important;
  background: #ffffff !important;
  box-shadow: 0 2px 10px rgba(194, 122, 59, 0.25);
  padding: 8px 14px;
}
.ghost-btn.is-disabled {
  box-shadow: none;
}
.ghost-btn:hover,
.ghost-btn:focus {
  color: #ffffff !important;
  background: var(--ghost-color) !important;
  border-color: var(--ghost-color) !important;
}

/* 覆盖 Element Plus 的 radio-button 激活样式，使其使用主题色 */
.algorithm-radio-group :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background-color: var(--primary-color) !important;
  border-color: var(--primary-color) !important;
  color: #ffffff !important;
  box-shadow: -1px 0 0 0 var(--primary-color) !important;
}

.algorithm-radio-group :deep(.el-radio-button__inner:hover) {
  color: var(--primary-color) !important;
}

.algorithm-radio-group :deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-left: 1px solid #dcdfe6;
  border-radius: 4px 0 0 4px;
}

.algorithm-radio-group :deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 0 4px 4px 0;
}

@media screen and (max-width: 768px) {
  .cluster-container {
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
  }
  .kpi-cards-grid {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  }
}
</style>
