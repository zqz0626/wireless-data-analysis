<template>
  <div class="predict-container">
    <h1>预测分析</h1>
    
    <!-- 数据源选择：完全对齐预处理模块 -->
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

    <!-- 文件信息：完全对齐预处理模块 -->
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
    
    <!-- 预测配置：结构对齐聚类配置 -->
    <el-card shadow="never" v-if="fileInfo">
      <template #header>
        <div class="card-header"><span>预测配置</span></div>
      </template>
      <el-collapse v-model="activePredictPanels" class="config-collapse">
        <!-- 地区选择：复用聚类配置的样式 -->
        <el-collapse-item title="地区选择" name="areas">
          <div class="config-section">
            <div class="feature-selection-area">
              <div class="select-all-container">
                <el-checkbox v-model="isAllAreasSelected" @change="handleAreasSelectAll" size="small">全选</el-checkbox>
                <el-input
                  v-model="areaSearchKeyword"
                  size="small"
                  placeholder="搜索地区"
                  clearable
                  class="area-search-input"
                />
              </div>
              <div class="feature-list">
                <el-checkbox-group v-model="selectedAreas" @change="handleAreasSelect" :disabled="isUsingTemplate">
                  <el-checkbox
                    v-for="area in filteredAreaColumns"
                    :key="area"
                    :label="area"
                    size="small"
                    class="feature-checkbox"
                    :disabled="isUsingTemplate"
                  >{{ area }}</el-checkbox>
                </el-checkbox-group>
              </div>
              <div class="selected-features-display" v-if="filteredSelectedAreas.length">
                <span class="selection-label">已选择地区：</span>
                <el-tag
                  v-for="area in filteredSelectedAreas"
                  :key="area"
                  closable
                  size="small"
                  class="feature-tag"
                  @close="removeArea(area)"
                >{{ area }}</el-tag>
              </div>
            </div>
          </div>
        </el-collapse-item>

        <!-- 模型选择：参照特征选择样式，多选算法 -->
        <el-collapse-item title="模型选择" name="models">
          <div class="config-section">
            <div class="feature-selection-area">
              <div class="select-all-container">
                <el-checkbox v-model="isAllModelsSelected" @change="handleModelsSelectAll" size="small">全选</el-checkbox>
              </div>
              <div class="feature-list">
                <el-checkbox-group v-model="selectedModels" @change="handleModelsSelect">
                  <!-- 统计模型 -->
                  <div class="model-category">
                    <span class="category-title">统计模型：</span>
                    <el-checkbox label="stl_reg" size="small" class="feature-checkbox">STL + 线性回归</el-checkbox>
                    <el-checkbox label="sarima" size="small" class="feature-checkbox">SARIMA（季节 ARIMA）</el-checkbox>
                  </div>
                  <!-- 机器学习模型 -->
                  <div class="model-category">
                    <span class="category-title">机器学习模型：</span>
                    <el-checkbox label="xgboost" size="small" class="feature-checkbox">XGBoost 回归</el-checkbox>
                    <el-checkbox label="lightgbm" size="small" class="feature-checkbox">LightGBM 回归</el-checkbox>
                    <el-checkbox label="catboost" size="small" class="feature-checkbox">CatBoost 回归</el-checkbox>
                    <el-checkbox label="xgb_rf_residual" size="small" class="feature-checkbox">XGBoost + 随机森林（残差）</el-checkbox>
                  </div>
                  <!-- 深度学习模型 -->
                  <div class="model-category">
                    <span class="category-title">深度学习模型：</span>
                    <el-checkbox label="lstm" size="small" class="feature-checkbox">LSTM 神经网络</el-checkbox>
                    <el-checkbox label="gru" size="small" class="feature-checkbox">GRU 神经网络</el-checkbox>
                    <el-checkbox label="cnn" size="small" class="feature-checkbox">CNN 卷积神经网络</el-checkbox>
                    <el-checkbox label="tcn" size="small" class="feature-checkbox">TCN 时间卷积网络</el-checkbox>
                  </div>
                  <!-- 大模型 -->
                  <div class="model-category">
                    <span class="category-title">大模型：</span>
                    <el-checkbox label="llm_forecast" size="small" class="feature-checkbox">
                      大模型预测（gpt-oss:20b）
                    </el-checkbox>
                  </div>
                </el-checkbox-group>
              </div>
              <div class="selected-features-display" v-if="selectedModels.length">
                <span class="selection-label">已选择模型：</span>
                <el-tag
                  v-for="model in selectedModels"
                  :key="model"
                  closable
                  size="small"
                  class="feature-tag"
                  @close="removeModel(model)"
                >{{ getModelName(model) }}</el-tag>
              </div>
            </div>
          </div>
        </el-collapse-item>

        <!-- 算法参数：使用与聚类相同的 params-grid 风格 -->
        <el-collapse-item title="模型参数" name="params">
          <div class="config-section">
            <div class="params-grid vertical-params">
              <!-- STL + 回归 参数 -->
              <template v-if="selectedModels.includes('stl_reg')">
                <div class="param-item algo-block">
                  <div class="param-title-row">
                    <div class="param-title">STL + 线性回归</div>
                    <el-button
                      link
                      type="primary"
                      size="small"
                      @click="toggleParamCollapse('stl_reg')"
                    >{{ paramCollapsed.stl_reg ? '展开' : '收起' }}</el-button>
                  </div>
                  <div class="param-desc small-text text-gray-500">当前使用 STL 分解日周期结合线性/多项式回归趋势建模，可在此处调整关键参数。</div>
                  <div v-show="!paramCollapsed.stl_reg">
                    <div class="param-row">
                      <span class="param-label">季节周期 period：</span>
                      <el-input-number
                        v-model="modelParams.stl_reg.period"
                        :min="2"
                        :max="10000"
                        size="small"
                      />
                      <span class="small-text">（例如 144=1天，288=2天，单位：时间步）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">趋势阶数 degree：</span>
                      <el-select v-model="modelParams.stl_reg.degree" size="small" style="width: 120px;">
                        <el-option :value="1" label="1 阶（线性）" />
                        <el-option :value="2" label="2 阶（抛物线）" />
                        <el-option :value="3" label="3 阶（更灵活）" />
                      </el-select>
                    </div>
                    <div class="param-row">
                      <el-checkbox v-model="modelParams.stl_reg.robust" size="small">
                        使用鲁棒 STL（抗异常值）
                      </el-checkbox>
                    </div>
                    <div class="param-row">
                      <span class="param-label">窗口天数 days_window：</span>
                      <el-input-number
                        v-model="modelParams.stl_reg.days_window"
                        :min="0"
                        :max="180"
                        size="small"
                      />
                      <span class="small-text">（0 或不填：使用全部数据；&gt;0：仅使用最近 N 天数据建模）</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- 本地大模型预测 参数 -->
              <template v-if="selectedModels.includes('llm_forecast')">
                <div class="param-item algo-block">
                  <div class="param-title-row">
                    <div class="param-title">本地大模型预测</div>
                    <el-button
                      link
                      type="primary"
                      size="small"
                      @click="toggleParamCollapse('llm_forecast')"
                    >{{ paramCollapsed.llm_forecast ? '展开' : '收起' }}</el-button>
                  </div>
                  <div class="param-desc small-text text-gray-500">
                    使用本地 Ollama 大模型进行时间序列预测，可在此处控制采样温度、超时时间和窗口天数等关键参数。
                  </div>
                  <div v-show="!paramCollapsed.llm_forecast">
                    <div class="param-row">
                      <span class="param-label">采样温度 temperature：</span>
                      <el-input-number
                        v-model="modelParams.llm_forecast.temperature"
                        :min="0"
                        :max="1"
                        :step="0.05"
                        size="small"
                      />
                      <span class="small-text">（越低越保守，越高越随机，一般建议 0.0~0.3）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">超时时间 timeout（秒）：</span>
                      <el-input-number
                        v-model="modelParams.llm_forecast.timeout"
                        :min="30"
                        :max="600"
                        size="small"
                      />
                      <span class="small-text">（HTTP 请求超时时间，单位秒）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">窗口天数 days_window：</span>
                      <el-input-number
                        v-model="modelParams.llm_forecast.days_window"
                        :min="0"
                        :max="180"
                        size="small"
                      />
                      <span class="small-text">（0：使用全部数据；&gt;0：仅使用最近 N 天数据建模）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">每步 token 数 tokens_per_step：</span>
                      <el-input-number
                        v-model="modelParams.llm_forecast.tokens_per_step"
                        :min="1"
                        :max="16"
                        size="small"
                      />
                      <span class="small-text">（用于近似 num_predict = max(32, horizon × 此值)，数值越大生成越长）</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- SARIMA 参数 -->
              <template v-if="selectedModels.includes('sarima')">
                <div class="param-item algo-block">
                  <div class="param-title-row">
                    <div class="param-title">SARIMA（季节 ARIMA）</div>
                    <el-button
                      link
                      type="primary"
                      size="small"
                      @click="toggleParamCollapse('sarima')"
                    >{{ paramCollapsed.sarima ? '展开' : '收起' }}</el-button>
                  </div>
                  <div class="param-desc small-text text-gray-500">使用季节 ARIMA 模型（SARIMAX）对时间序列进行建模，可通过差分和季节项捕获趋势与周期。</div>
                  <div v-show="!paramCollapsed.sarima">
                    <div class="param-row">
                      <span class="param-label">非季节阶数 (p,d,q)：</span>
                      <el-input-number v-model="modelParams.sarima.order_p" :min="0" :max="5" size="small" />
                      <el-input-number v-model="modelParams.sarima.order_d" :min="0" :max="2" size="small" />
                      <el-input-number v-model="modelParams.sarima.order_q" :min="0" :max="5" size="small" />
                    </div>
                    <div class="param-row">
                      <span class="param-label">季节阶数 (P,D,Q)：</span>
                      <el-input-number v-model="modelParams.sarima.seasonal_P" :min="0" :max="3" size="small" />
                      <el-input-number v-model="modelParams.sarima.seasonal_D" :min="0" :max="2" size="small" />
                      <el-input-number v-model="modelParams.sarima.seasonal_Q" :min="0" :max="3" size="small" />
                    </div>
                    <div class="param-row">
                      <span class="param-label">季节周期 seasonal_period：</span>
                      <el-input-number
                        v-model="modelParams.sarima.seasonal_period"
                        :min="2"
                        :max="10000"
                        size="small"
                      />
                      <span class="small-text">（例如 140 或 144，对应 1 天周期）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">窗口天数 days_window：</span>
                      <el-input-number
                        v-model="modelParams.sarima.days_window"
                        :min="0"
                        :max="180"
                        size="small"
                      />
                      <span class="small-text">（0 或不填：使用全部数据；&gt;0：仅使用最近 N 天数据建模）</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- XGBoost 参数 -->
              <template v-if="selectedModels.includes('xgboost')">
                <div class="param-item algo-block">
                  <div class="param-title-row">
                    <div class="param-title">XGBoost 回归</div>
                    <el-button
                      link
                      type="primary"
                      size="small"
                      @click="toggleParamCollapse('xgboost')"
                    >{{ paramCollapsed.xgboost ? '展开' : '收起' }}</el-button>
                  </div>
                  <div class="param-desc small-text text-gray-500">使用梯度提升树对时间序列构造滞后特征进行回归预测，作为机器学习基线模型。</div>
                  <div v-show="!paramCollapsed.xgboost">
                    <div class="param-row">
                      <span class="param-label">滞后阶数 lag：</span>
                      <el-input-number
                        v-model="modelParams.xgboost.lag"
                        :min="1"
                        :max="200"
                        size="small"
                      />
                      <span class="small-text">（使用最近 N 个时间步作为特征）</span>
                    </div>
                    <div class="param-row">
                      <el-checkbox v-model="modelParams.xgboost.use_trend_features" size="small">
                        启用趋势特征
                      </el-checkbox>
                      <span class="small-text ml-2" v-if="modelParams.xgboost.use_trend_features">
                        趋势阶数：
                        <el-input-number
                          v-model="modelParams.xgboost.trend_degree"
                          :min="1"
                          :max="3"
                          size="small"
                          style="margin-left: 6px;"
                        />
                      </span>
                    </div>
                    <div class="param-row">
                      <el-checkbox v-model="modelParams.xgboost.use_seasonal_features" size="small">
                        启用季节特征（正弦/余弦）
                      </el-checkbox>
                      <span class="small-text ml-2" v-if="modelParams.xgboost.use_seasonal_features">
                        谐波数量：
                        <el-input-number
                          v-model="modelParams.xgboost.seasonal_harmonics"
                          :min="1"
                          :max="6"
                          size="small"
                          style="margin-left: 6px;"
                        />
                      </span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">弱学习器数 n_estimators：</span>
                      <el-input-number
                        v-model="modelParams.xgboost.n_estimators"
                        :min="50"
                        :max="1000"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">最大深度 max_depth：</span>
                      <el-input-number
                        v-model="modelParams.xgboost.max_depth"
                        :min="2"
                        :max="10"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">学习率 learning_rate：</span>
                      <el-input-number
                        v-model="modelParams.xgboost.learning_rate"
                        :min="0.001"
                        :max="0.5"
                        :step="0.01"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">子采样 subsample：</span>
                      <el-input-number
                        v-model="modelParams.xgboost.subsample"
                        :min="0.1"
                        :max="1"
                        :step="0.05"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">列采样 colsample_bytree：</span>
                      <el-input-number
                        v-model="modelParams.xgboost.colsample_bytree"
                        :min="0.1"
                        :max="1"
                        :step="0.05"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">季节周期 seasonal_period：</span>
                      <el-input-number
                        v-model="modelParams.xgboost.seasonal_period"
                        :min="2"
                        :max="10000"
                        size="small"
                      />
                      <span class="small-text">（用于 days_window 估算点数，如 140≈1天）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">窗口天数 days_window：</span>
                      <el-input-number
                        v-model="modelParams.xgboost.days_window"
                        :min="0"
                        :max="180"
                        size="small"
                      />
                      <span class="small-text">（0：使用全部数据；&gt;0：仅使用最近 N 天数据建模）</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- LightGBM 参数（样式与 XGBoost 保持一致） -->
              <template v-if="selectedModels.includes('lightgbm')">
                <div class="param-item algo-block">
                  <div class="param-title-row">
                    <div class="param-title">LightGBM 回归</div>
                    <el-button
                      link
                      type="primary"
                      size="small"
                      @click="toggleParamCollapse('lightgbm')"
                    >{{ paramCollapsed.lightgbm ? '展开' : '收起' }}</el-button>
                  </div>
                  <div class="param-desc small-text text-gray-500">使用梯度提升树对时间序列构造滞后特征进行回归预测，特征工程与 XGBoost 一致，便于对比效果。</div>
                  <div v-show="!paramCollapsed.lightgbm">
                    <div class="param-row">
                      <span class="param-label">滞后阶数 lag：</span>
                      <el-input-number
                        v-model="modelParams.lightgbm.lag"
                        :min="1"
                        :max="288"
                        size="small"
                      />
                      <span class="small-text">（使用最近 N 个时间步作为特征）</span>
                    </div>
                    <div class="param-row">
                      <el-checkbox v-model="modelParams.lightgbm.use_trend_features" size="small">
                        启用趋势特征
                      </el-checkbox>
                      <span class="small-text ml-2" v-if="modelParams.lightgbm.use_trend_features">
                        趋势阶数：
                        <el-input-number
                          v-model="modelParams.lightgbm.trend_degree"
                          :min="1"
                          :max="3"
                          size="small"
                          style="margin-left: 6px;"
                        />
                      </span>
                    </div>
                    <div class="param-row">
                      <el-checkbox v-model="modelParams.lightgbm.use_seasonal_features" size="small">
                        启用季节特征（正弦/余弦）
                      </el-checkbox>
                      <span class="small-text ml-2" v-if="modelParams.lightgbm.use_seasonal_features">
                        谐波数量：
                        <el-input-number
                          v-model="modelParams.lightgbm.seasonal_harmonics"
                          :min="1"
                          :max="10"
                          size="small"
                          style="margin-left: 6px;"
                        />
                      </span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">弱学习器数 n_estimators：</span>
                      <el-input-number
                        v-model="modelParams.lightgbm.n_estimators"
                        :min="50"
                        :max="2000"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">最大深度 max_depth：</span>
                      <el-input-number
                        v-model="modelParams.lightgbm.max_depth"
                        :min="-1"
                        :max="32"
                        size="small"
                      />
                      <span class="small-text">（-1 表示不限深度）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">学习率 learning_rate：</span>
                      <el-input-number
                        v-model="modelParams.lightgbm.learning_rate"
                        :min="0.001"
                        :max="0.5"
                        :step="0.01"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">子采样 subsample：</span>
                      <el-input-number
                        v-model="modelParams.lightgbm.subsample"
                        :min="0.1"
                        :max="1"
                        :step="0.05"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">列采样 colsample_bytree：</span>
                      <el-input-number
                        v-model="modelParams.lightgbm.colsample_bytree"
                        :min="0.1"
                        :max="1"
                        :step="0.05"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">季节周期 seasonal_period：</span>
                      <el-input-number
                        v-model="modelParams.lightgbm.seasonal_period"
                        :min="2"
                        :max="10000"
                        size="small"
                      />
                      <span class="small-text">（用于 days_window 估算点数，如 140≈1天）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">窗口天数 days_window：</span>
                      <el-input-number
                        v-model="modelParams.lightgbm.days_window"
                        :min="0"
                        :max="180"
                        size="small"
                      />
                      <span class="small-text">（0：使用全部数据；&gt;0：仅使用最近 N 天数据建模）</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- CatBoost 参数（样式与 XGBoost 保持一致） -->
              <template v-if="selectedModels.includes('catboost')">
                <div class="param-item algo-block">
                  <div class="param-title-row">
                    <div class="param-title">CatBoost 回归</div>
                    <el-button
                      link
                      type="primary"
                      size="small"
                      @click="toggleParamCollapse('catboost')"
                    >{{ paramCollapsed.catboost ? '展开' : '收起' }}</el-button>
                  </div>
                  <div class="param-desc small-text text-gray-500">使用 CatBoost 梯度提升树对时间序列进行回归预测，适合对不平滑序列建模。</div>
                  <div v-show="!paramCollapsed.catboost">
                    <div class="param-row">
                      <span class="param-label">滞后阶数 lag：</span>
                      <el-input-number
                        v-model="modelParams.catboost.lag"
                        :min="1"
                        :max="288"
                        size="small"
                      />
                      <span class="small-text">（使用最近 N 个时间步作为特征）</span>
                    </div>
                    <div class="param-row">
                      <el-checkbox v-model="modelParams.catboost.use_trend_features" size="small">
                        启用趋势特征
                      </el-checkbox>
                      <span class="small-text ml-2" v-if="modelParams.catboost.use_trend_features">
                        趋势阶数：
                        <el-input-number
                          v-model="modelParams.catboost.trend_degree"
                          :min="1"
                          :max="3"
                          size="small"
                          style="margin-left: 6px;"
                        />
                      </span>
                    </div>
                    <div class="param-row">
                      <el-checkbox v-model="modelParams.catboost.use_seasonal_features" size="small">
                        启用季节特征（正弦/余弦）
                      </el-checkbox>
                      <span class="small-text ml-2" v-if="modelParams.catboost.use_seasonal_features">
                        谐波数量：
                        <el-input-number
                          v-model="modelParams.catboost.seasonal_harmonics"
                          :min="1"
                          :max="10"
                          size="small"
                          style="margin-left: 6px;"
                        />
                      </span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">弱学习器数 iterations：</span>
                      <el-input-number
                        v-model="modelParams.catboost.iterations"
                        :min="50"
                        :max="2000"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">树深度 depth：</span>
                      <el-input-number
                        v-model="modelParams.catboost.depth"
                        :min="2"
                        :max="16"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">学习率 learning_rate：</span>
                      <el-input-number
                        v-model="modelParams.catboost.learning_rate"
                        :min="0.001"
                        :max="0.5"
                        :step="0.01"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">季节周期 seasonal_period：</span>
                      <el-input-number
                        v-model="modelParams.catboost.seasonal_period"
                        :min="2"
                        :max="10000"
                        size="small"
                      />
                      <span class="small-text">（用于 days_window 估算点数，如 140≈1天）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">窗口天数 days_window：</span>
                      <el-input-number
                        v-model="modelParams.catboost.days_window"
                        :min="0"
                        :max="180"
                        size="small"
                      />
                      <span class="small-text">（0：使用全部数据；&gt;0：仅使用最近 N 天数据建模）</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- XGBoost + 随机森林 残差 参数 -->
              <template v-if="selectedModels.includes('xgb_rf_residual')">
                <div class="param-item algo-block">
                  <div class="param-title-row">
                    <div class="param-title">XGBoost + 随机森林（残差）</div>
                    <el-button
                      link
                      type="primary"
                      size="small"
                      @click="toggleParamCollapse('xgb_rf_residual')"
                    >{{ paramCollapsed.xgb_rf_residual ? '展开' : '收起' }}</el-button>
                  </div>
                  <div class="param-desc small-text text-gray-500">
                    先由 XGBoost 建立主预测，再用随机森林拟合残差并叠加，可在此分别调整两部分参数。
                  </div>

                  <div v-show="!paramCollapsed.xgb_rf_residual">
                    <!-- 主模型 XGBoost 部分 -->
                    <div class="param-row">
                      <span class="param-label">滞后阶数 lag：</span>
                      <el-input-number
                        v-model="modelParams.xgb_rf_residual.lag"
                        :min="1"
                        :max="200"
                        size="small"
                      />
                      <span class="small-text">（XGBoost 主模型使用最近 N 个时间步作为特征）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">弱学习器数 n_estimators：</span>
                      <el-input-number
                        v-model="modelParams.xgb_rf_residual.n_estimators"
                        :min="50"
                        :max="1000"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">最大深度 max_depth：</span>
                      <el-input-number
                        v-model="modelParams.xgb_rf_residual.max_depth"
                        :min="2"
                        :max="10"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">学习率 learning_rate：</span>
                      <el-input-number
                        v-model="modelParams.xgb_rf_residual.learning_rate"
                        :min="0.001"
                        :max="0.5"
                        :step="0.01"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">子采样 subsample：</span>
                      <el-input-number
                        v-model="modelParams.xgb_rf_residual.subsample"
                        :min="0.1"
                        :max="1"
                        :step="0.05"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">列采样 colsample_bytree：</span>
                      <el-input-number
                        v-model="modelParams.xgb_rf_residual.colsample_bytree"
                        :min="0.1"
                        :max="1"
                        :step="0.05"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <el-checkbox v-model="modelParams.xgb_rf_residual.use_trend_features" size="small">
                        启用趋势特征
                      </el-checkbox>
                      <span class="small-text ml-2" v-if="modelParams.xgb_rf_residual.use_trend_features">
                        趋势阶数：
                        <el-input-number
                          v-model="modelParams.xgb_rf_residual.trend_degree"
                          :min="1"
                          :max="3"
                          size="small"
                          style="margin-left: 6px;"
                        />
                      </span>
                    </div>
                    <div class="param-row">
                      <el-checkbox v-model="modelParams.xgb_rf_residual.use_seasonal_features" size="small">
                        启用季节特征（正弦/余弦）
                      </el-checkbox>
                      <span class="small-text ml-2" v-if="modelParams.xgb_rf_residual.use_seasonal_features">
                        谐波数量：
                        <el-input-number
                          v-model="modelParams.xgb_rf_residual.seasonal_harmonics"
                          :min="1"
                          :max="6"
                          size="small"
                          style="margin-left: 6px;"
                        />
                      </span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">季节周期 seasonal_period：</span>
                      <el-input-number
                        v-model="modelParams.xgb_rf_residual.seasonal_period"
                        :min="2"
                        :max="10000"
                        size="small"
                      />
                      <span class="small-text">（例如 144 ≈ 1 天周期）</span>
                    </div>

                    <!-- 残差随机森林部分 -->
                    <div class="param-row" style="margin-top: 8px;">
                      <span class="param-label">RF 树数量 rf_n_estimators：</span>
                      <el-input-number
                        v-model="modelParams.xgb_rf_residual.rf_n_estimators"
                        :min="10"
                        :max="500"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">RF 最大深度 rf_max_depth：</span>
                      <el-input-number
                        v-model="modelParams.xgb_rf_residual.rf_max_depth"
                        :min="1"
                        :max="50"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">RF 最小分割样本 rf_min_samples_split：</span>
                      <el-input-number
                        v-model="modelParams.xgb_rf_residual.rf_min_samples_split"
                        :min="2"
                        :max="20"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">RF 最小叶节点样本 rf_min_samples_leaf：</span>
                      <el-input-number
                        v-model="modelParams.xgb_rf_residual.rf_min_samples_leaf"
                        :min="1"
                        :max="10"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">RF 最大特征数 rf_max_features：</span>
                      <el-select v-model="modelParams.xgb_rf_residual.rf_max_features" size="small" style="width: 100px;">
                        <el-option label="sqrt" value="sqrt" />
                        <el-option label="log2" value="log2" />
                        <el-option label="None" value="null" />
                      </el-select>
                    </div>
                    <div class="param-row">
                      <el-checkbox v-model="modelParams.xgb_rf_residual.rf_bootstrap" size="small">
                        RF 启用Bootstrap采样
                      </el-checkbox>
                      <span class="small-text ml-2">（是否对残差模型使用 Bootstrap）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">RF 随机种子 rf_random_state：</span>
                      <el-input-number
                        v-model="modelParams.xgb_rf_residual.rf_random_state"
                        :min="0"
                        :max="1000"
                        size="small"
                      />
                    </div>
                    <div class="param-row">
                      <span class="param-label">残差权重 rf_residual_weight：</span>
                      <el-input-number
                        v-model="modelParams.xgb_rf_residual.rf_residual_weight"
                        :min="0.0"
                        :max="3.0"
                        :step="0.1"
                        size="small"
                      />
                      <span class="small-text">（1=正常残差；&gt;1 更“凶”，放大 RF 校正）</span>
                    </div>

                    <!-- 将窗口天数放在整个块的最后一行 -->
                    <div class="param-row">
                      <span class="param-label">窗口天数 days_window：</span>
                      <el-input-number
                        v-model="modelParams.xgb_rf_residual.days_window"
                        :min="0"
                        :max="180"
                        size="small"
                      />
                      <span class="small-text">（0：使用全部数据；&gt;0：仅使用最近 N 天数据建模）</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- LSTM 神经网络 参数 -->
              <template v-if="selectedModels.includes('lstm')">
                <div class="param-item algo-block">
                  <div class="param-title-row">
                    <div class="param-title">LSTM 神经网络</div>
                    <el-button
                      link
                      type="primary"
                      size="small"
                      @click="toggleParamCollapse('lstm')"
                    >{{ paramCollapsed.lstm ? '展开' : '收起' }}</el-button>
                  </div>
                  <div class="param-desc small-text text-gray-500">使用长短期记忆网络(LSTM)进行时间序列预测，能够捕捉长期依赖关系，适合复杂的非线性时间序列数据。</div>
                  <div v-show="!paramCollapsed.lstm">
                    <div class="param-row">
                      <span class="param-label">序列长度 sequence_length：</span>
                      <el-input-number
                        v-model="modelParams.lstm.sequence_length"
                        :min="24"
                        :max="720"
                        size="small"
                      />
                      <span class="small-text">（输入序列的时间步数）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">隐藏层大小 hidden_size：</span>
                      <el-input-number
                        v-model="modelParams.lstm.hidden_size"
                        :min="16"
                        :max="256"
                        size="small"
                      />
                      <span class="small-text">（LSTM隐藏单元数量）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">网络层数 num_layers：</span>
                      <el-input-number
                        v-model="modelParams.lstm.num_layers"
                        :min="1"
                        :max="4"
                        size="small"
                      />
                      <span class="small-text">（LSTM层的数量）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">Dropout比率 dropout：</span>
                      <el-input-number
                        v-model="modelParams.lstm.dropout"
                        :min="0"
                        :max="0.5"
                        :step="0.05"
                        size="small"
                      />
                      <span class="small-text">（防止过拟合的dropout比率）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">学习率 learning_rate：</span>
                      <el-input-number
                        v-model="modelParams.lstm.learning_rate"
                        :min="0.0001"
                        :max="0.01"
                        :step="0.0001"
                        size="small"
                      />
                      <span class="small-text">（优化器学习率）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">训练轮数 epochs：</span>
                      <el-input-number
                        v-model="modelParams.lstm.epochs"
                        :min="10"
                        :max="500"
                        size="small"
                      />
                      <span class="small-text">（训练的最大轮数）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">批次大小 batch_size：</span>
                      <el-input-number
                        v-model="modelParams.lstm.batch_size"
                        :min="8"
                        :max="128"
                        size="small"
                      />
                      <span class="small-text">（训练批次大小）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">早停耐心值 early_stopping_patience：</span>
                      <el-input-number
                        v-model="modelParams.lstm.early_stopping_patience"
                        :min="5"
                        :max="50"
                        size="small"
                      />
                      <span class="small-text">（早停的耐心值，0表示禁用）</span>
                    </div>
                    <div class="param-row">
                      <el-checkbox v-model="modelParams.lstm.bidirectional" size="small">
                        启用双向LSTM
                      </el-checkbox>
                      <span class="small-text ml-2">（使用双向LSTM增强特征提取）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">窗口天数 days_window：</span>
                      <el-input-number
                        v-model="modelParams.lstm.days_window"
                        :min="0"
                        :max="180"
                        size="small"
                      />
                      <span class="small-text">（0：使用全部数据；&gt;0：仅使用最近 N 天数据建模）</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- GRU 神经网络 参数 -->
              <template v-if="selectedModels.includes('gru')">
                <div class="param-item algo-block">
                  <div class="param-title-row">
                    <div class="param-title">GRU 神经网络</div>
                    <el-button
                      link
                      type="primary"
                      size="small"
                      @click="toggleParamCollapse('gru')"
                    >{{ paramCollapsed.gru ? '展开' : '收起' }}</el-button>
                  </div>
                  <div class="param-desc small-text text-gray-500">使用门控循环单元(GRU)进行时间序列预测，结构较 LSTM 更简洁，训练更快。</div>
                  <div v-show="!paramCollapsed.gru">
                    <div class="param-row">
                      <span class="param-label">序列长度 sequence_length：</span>
                      <el-input-number
                        v-model="modelParams.gru.sequence_length"
                        :min="24"
                        :max="720"
                        size="small"
                      />
                      <span class="small-text">（输入序列的时间步数）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">隐藏层大小 hidden_size：</span>
                      <el-input-number
                        v-model="modelParams.gru.hidden_size"
                        :min="16"
                        :max="256"
                        size="small"
                      />
                      <span class="small-text">（GRU 隐藏单元数量）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">网络层数 num_layers：</span>
                      <el-input-number
                        v-model="modelParams.gru.num_layers"
                        :min="1"
                        :max="4"
                        size="small"
                      />
                      <span class="small-text">（GRU 层的数量）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">Dropout 比率 dropout：</span>
                      <el-input-number
                        v-model="modelParams.gru.dropout"
                        :min="0"
                        :max="0.5"
                        :step="0.05"
                        size="small"
                      />
                      <span class="small-text">（防止过拟合的 dropout 比率）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">学习率 learning_rate：</span>
                      <el-input-number
                        v-model="modelParams.gru.learning_rate"
                        :min="0.0001"
                        :max="0.01"
                        :step="0.0001"
                        size="small"
                      />
                      <span class="small-text">（优化器学习率）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">训练轮数 epochs：</span>
                      <el-input-number
                        v-model="modelParams.gru.epochs"
                        :min="10"
                        :max="500"
                        size="small"
                      />
                      <span class="small-text">（训练的最大轮数）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">批次大小 batch_size：</span>
                      <el-input-number
                        v-model="modelParams.gru.batch_size"
                        :min="8"
                        :max="128"
                        size="small"
                      />
                      <span class="small-text">（训练批次大小）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">早停耐心值 early_stopping_patience：</span>
                      <el-input-number
                        v-model="modelParams.gru.early_stopping_patience"
                        :min="5"
                        :max="50"
                        size="small"
                      />
                      <span class="small-text">（早停的耐心值，0 表示禁用）</span>
                    </div>
                    <div class="param-row">
                      <el-checkbox v-model="modelParams.gru.bidirectional" size="small">
                        启用双向 GRU
                      </el-checkbox>
                      <span class="small-text ml-2">（使用双向 GRU 增强特征提取）</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">窗口天数 days_window：</span>
                      <el-input-number
                        v-model="modelParams.gru.days_window"
                        :min="0"
                        :max="180"
                        size="small"
                      />
                      <span class="small-text">（0：使用全部数据；>0：仅使用最近 N 天数据建模）</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- CNN 卷积神经网络 参数 -->
              <template v-if="selectedModels.includes('cnn')">
                <div class="param-item algo-block">
                  <div class="param-title-row">
                    <div class="param-title">CNN 卷积神经网络</div>
                    <el-button
                      link
                      type="primary"
                      size="small"
                      @click="toggleParamCollapse('cnn')"
                    >{{ paramCollapsed.cnn ? '展开' : '收起' }}</el-button>
                  </div>
                  <div class="param-desc small-text text-gray-500">
                    使用一维卷积网络从固定长度时间窗口中提取局部模式，对下一时间步进行回归预测。
                  </div>

                  <div v-show="!paramCollapsed.cnn">
                    <div class="param-row">
                      <span class="param-label">序列长度 sequence_length：</span>
                      <el-input-number
                        v-model="modelParams.cnn.sequence_length"
                        :min="16"
                        :max="1000"
                        size="small"
                      />
                      <span class="small-text">（输入时间步数量，例如 144≈1天）</span>
                    </div>

                    <div class="param-row">
                      <span class="param-label">卷积通道数 num_filters：</span>
                      <el-input-number
                        v-model="modelParams.cnn.num_filters"
                        :min="4"
                        :max="256"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">卷积核大小 kernel_size：</span>
                      <el-input-number
                        v-model="modelParams.cnn.kernel_size"
                        :min="2"
                        :max="31"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">卷积层数 num_layers：</span>
                      <el-input-number
                        v-model="modelParams.cnn.num_layers"
                        :min="1"
                        :max="4"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">全连接维度 hidden_size：</span>
                      <el-input-number
                        v-model="modelParams.cnn.hidden_size"
                        :min="16"
                        :max="256"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">Dropout：</span>
                      <el-input-number
                        v-model="modelParams.cnn.dropout"
                        :min="0"
                        :max="0.9"
                        :step="0.05"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">学习率 learning_rate：</span>
                      <el-input-number
                        v-model="modelParams.cnn.learning_rate"
                        :min="0.0001"
                        :max="0.1"
                        :step="0.0001"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">训练轮数 epochs：</span>
                      <el-input-number
                        v-model="modelParams.cnn.epochs"
                        :min="10"
                        :max="500"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">批次大小 batch_size：</span>
                      <el-input-number
                        v-model="modelParams.cnn.batch_size"
                        :min="8"
                        :max="512"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">早停耐心 early_stopping_patience：</span>
                      <el-input-number
                        v-model="modelParams.cnn.early_stopping_patience"
                        :min="0"
                        :max="50"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">窗口天数 days_window：</span>
                      <el-input-number
                        v-model="modelParams.cnn.days_window"
                        :min="0"
                        :max="180"
                        size="small"
                      />
                      <span class="small-text">（0：使用全部数据；&gt;0：仅使用最近 N 天数据建模）</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- TCN 时间卷积网络 参数 -->
              <template v-if="selectedModels.includes('tcn')">
                <div class="param-item algo-block">
                  <div class="param-title-row">
                    <div class="param-title">TCN 时间卷积网络</div>
                    <el-button
                      link
                      type="primary"
                      size="small"
                      @click="toggleParamCollapse('tcn')"
                    >{{ paramCollapsed.tcn ? '展开' : '收起' }}</el-button>
                  </div>
                  <div class="param-desc small-text text-gray-500">
                    使用一维膨胀卷积的时间卷积网络(TCN)，在固定长度时间窗口上建模长程依赖并进行回归预测。
                  </div>

                  <div v-show="!paramCollapsed.tcn">
                    <div class="param-row">
                      <span class="param-label">序列长度 sequence_length：</span>
                      <el-input-number
                        v-model="modelParams.tcn.sequence_length"
                        :min="16"
                        :max="1000"
                        size="small"
                      />
                      <span class="small-text">（输入时间步数量，例如 144≈1天）</span>
                    </div>

                    <div class="param-row">
                      <span class="param-label">卷积通道数 num_filters：</span>
                      <el-input-number
                        v-model="modelParams.tcn.num_filters"
                        :min="4"
                        :max="256"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">卷积核大小 kernel_size：</span>
                      <el-input-number
                        v-model="modelParams.tcn.kernel_size"
                        :min="2"
                        :max="31"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">卷积层数 num_layers：</span>
                      <el-input-number
                        v-model="modelParams.tcn.num_layers"
                        :min="1"
                        :max="6"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">全连接维度 hidden_size：</span>
                      <el-input-number
                        v-model="modelParams.tcn.hidden_size"
                        :min="16"
                        :max="256"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">Dropout：</span>
                      <el-input-number
                        v-model="modelParams.tcn.dropout"
                        :min="0"
                        :max="0.9"
                        :step="0.05"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">学习率 learning_rate：</span>
                      <el-input-number
                        v-model="modelParams.tcn.learning_rate"
                        :min="0.0001"
                        :max="0.1"
                        :step="0.0001"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">训练轮数 epochs：</span>
                      <el-input-number
                        v-model="modelParams.tcn.epochs"
                        :min="10"
                        :max="500"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">批次大小 batch_size：</span>
                      <el-input-number
                        v-model="modelParams.tcn.batch_size"
                        :min="8"
                        :max="512"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">早停耐心 early_stopping_patience：</span>
                      <el-input-number
                        v-model="modelParams.tcn.early_stopping_patience"
                        :min="0"
                        :max="50"
                        size="small"
                      />
                    </div>

                    <div class="param-row">
                      <span class="param-label">窗口天数 days_window：</span>
                      <el-input-number
                        v-model="modelParams.tcn.days_window"
                        :min="0"
                        :max="180"
                        size="small"
                      />
                      <span class="small-text">（0：使用全部数据；&gt;0：仅使用最近 N 天数据建模）</span>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>
    
    <!-- 执行按钮 -->
    <el-card shadow="never" class="execute-card" v-if="fileInfo">
      <template #header>
        <div class="card-header"><span>执行预测</span></div>
      </template>
      <div class="action-buttons">
        <el-button size="large" @click="runPredictForSelected" :loading="isPredicting">执行</el-button>
        <el-button size="large" @click="saveAsTemplate" :disabled="!canSaveTemplate">保存为模板</el-button>
        <el-button size="large" @click="resetPredictConfig">重置</el-button>
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
          <vxe-table-column field="config.models" title="模型数量" align="center" min-width="120" resizeable="false">
            <template #default="{ row }">{{ row.config.models.length }}</template>
          </vxe-table-column>
          <vxe-table-column field="config.areas" title="地区数量" align="center" min-width="120" resizeable="false">
            <template #default="{ row }">{{ row.config.areas.length }}</template>
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

    <!-- 预测结果：折线图展示 -->
    <el-card shadow="never" v-if="singleResult">
      <template #header>
        <div class="card-header">
          <span>预测结果</span>
          <el-select 
            v-model="selectedAreaForChart" 
            placeholder="选择地区" 
            style="width: 200px; margin-right: 12px;"
            @change="updateChart"
          >
            <el-option
              v-for="area in selectedAreas"
              :key="area"
              :label="area"
              :value="area"
            />
          </el-select>
          <div class="chart-toggle-group">
            <el-button
              size="small"
              class="chart-toggle-btn"
              :class="{ 'chart-toggle-btn-active': showActual }"
              @click="toggleChartLayer('actual')"
            >真实值</el-button>
            <el-button
              size="small"
              class="chart-toggle-btn"
              :class="{ 'chart-toggle-btn-active': showHistoryPred }"
              @click="toggleChartLayer('history')"
            >历史预测</el-button>
            <el-button
              size="small"
              class="chart-toggle-btn"
              :class="{ 'chart-toggle-btn-active': showFuturePred }"
              @click="toggleChartLayer('future')"
            >未来预测</el-button>
          </div>
        </div>
      </template>
      <div class="chart-wrapper">
        <div ref="chartRef" class="predict-chart"></div>
      </div>
    </el-card>

    <!-- 预测准确性评估 -->
    <el-card shadow="never" v-if="singleResult && selectedAreaForChart">
      <template #header>
        <div class="card-header">
          <span>预测准确性评估（测试集 1/4 区间）</span>
        </div>
      </template>
      <div class="accuracy-wrapper">
        <div v-if="modelAccuracyList.length === 0" class="accuracy-empty">
          <el-icon style="margin-right: 8px; color: #9ca3af;"><InfoFilled /></el-icon>
          <span>暂无可用的评估指标，请先执行预测。</span>
        </div>
        <el-table
          v-else
          :data="modelAccuracyListSorted"
          size="default"
          stripe
          style="width: 100%;"
          :header-cell-style="{ backgroundColor: '#f5f7fa', color: '#111827', fontWeight: 600 }"
          :default-sort="{ prop: 'score', order: 'descending' }"
          @sort-change="handleAccuracySortChange"
        >
          <el-table-column prop="modelName" label="模型" min-width="150" align="left" />
          <el-table-column prop="mae" label="MAE" min-width="110" align="right" sortable="custom">
            <template #default="scope">
              <span class="metric-number">{{ formatNumber(scope.row.mae) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="rmse" label="RMSE" min-width="110" align="right" sortable="custom">
            <template #default="scope">
              <span class="metric-number">{{ formatNumber(scope.row.rmse) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="score" label="评分" min-width="120" align="center" sortable="custom">
            <template #default="scope">
              <span class="score-number">{{ scope.row.score.toFixed(1) }}%</span>
            </template>
          </el-table-column>
          <el-table-column prop="grade" label="评级" min-width="90" align="center" sortable="custom">
            <template #default="scope">
              <el-tag
                :type="scope.row.grade === '优' ? 'success' : scope.row.grade === '良' ? 'primary' : scope.row.grade === '中' ? 'warning' : 'danger'"
                size="small"
                effect="light"
              >
                {{ scope.row.grade }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
        <div class="accuracy-details">
          <div class="rule-row">
            <div class="rule-item">
              <el-tag type="success" size="small" effect="plain">优</el-tag>
              <span class="rule-text">评分 ≥ 90</span>
            </div>
            <div class="rule-item">
              <el-tag type="primary" size="small" effect="plain">良</el-tag>
              <span class="rule-text">评分 ≥ 80</span>
            </div>
            <div class="rule-item">
              <el-tag type="warning" size="small" effect="plain">中</el-tag>
              <span class="rule-text">评分 ≥ 60</span>
            </div>
            <div class="rule-item">
              <el-tag type="danger" size="small" effect="plain">差</el-tag>
              <span class="rule-text">评分 &lt; 60</span>
            </div>
          </div>
          
          <div class="formula-grid">
            <div class="formula-item">
              <span class="formula-label">MAE</span>
              <span class="formula-eq">= Σ|y<sub>true</sub> - y<sub>pred</sub>| / n</span>
              <span class="formula-note">（测试集 1/4 区间）</span>
            </div>
            <div class="formula-item">
              <span class="formula-label">RMSE</span>
              <span class="formula-eq">= √(Σ(y<sub>true</sub> - y<sub>pred</sub>)² / n)</span>
            </div>
            <div class="formula-item">
              <span class="formula-label">综合相对误差</span>
              <span class="formula-eq">= 0.5 × MAE / mean(|y<sub>true</sub>|) + 0.5 × RMSE / mean(|y<sub>true</sub>|)</span>
            </div>
            <div class="formula-item">
              <span class="formula-label">评分</span>
              <span class="formula-eq">= 100 / (1 + 综合相对误差)</span>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 跨文件平均分 -->
    <el-card shadow="never" v-if="singleResult && modelCrossFileAverageList.length > 0">
      <template #header>
        <div class="card-header">
          <span>跨文件平均分（当前文件所有已预测地区）</span>
        </div>
      </template>
      <div class="accuracy-wrapper">
        <el-table
          :data="modelCrossFileAverageListSorted"
          size="default"
          stripe
          style="width: 100%;"
          :header-cell-style="{ backgroundColor: '#f0f9ff', color: '#111827', fontWeight: 600 }"
          :default-sort="{ prop: 'score', order: 'descending' }"
          @sort-change="handleCrossFileSortChange"
        >
          <el-table-column prop="modelName" label="模型" min-width="150" align="left" />
          <el-table-column prop="mae" label="平均 MAE" min-width="110" align="right" sortable="custom">
            <template #default="scope">
              <span class="metric-number">{{ formatNumber(scope.row.mae) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="rmse" label="平均 RMSE" min-width="110" align="right" sortable="custom">
            <template #default="scope">
              <span class="metric-number">{{ formatNumber(scope.row.rmse) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="score" label="平均评分" min-width="120" align="center" sortable="custom">
            <template #default="scope">
              <span class="score-number">{{ scope.row.score.toFixed(1) }}%</span>
            </template>
          </el-table-column>
          <el-table-column prop="grade" label="综合评级" min-width="90" align="center" sortable="custom">
            <template #default="scope">
              <el-tag
                :type="scope.row.grade === '优' ? 'success' : scope.row.grade === '良' ? 'primary' : scope.row.grade === '中' ? 'warning' : 'danger'"
                size="small"
                effect="light"
              >
                {{ scope.row.grade }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
        <div class="accuracy-details">
          <div class="formula-grid">
            <div class="formula-item">
              <span class="formula-label">平均 MAE</span>
              <span class="formula-eq">= Σ MAE<sub>i</sub> / k</span>
              <span class="formula-note">（i = 1..k，k 为地区数）</span>
            </div>
            <div class="formula-item">
              <span class="formula-label">平均 RMSE</span>
              <span class="formula-eq">= Σ RMSE<sub>i</sub> / k</span>
            </div>
            <div class="formula-item">
              <span class="formula-label">平均评分</span>
              <span class="formula-eq">= Σ 评分<sub>i</sub> / k</span>
            </div>
            <div class="formula-item">
              <span class="formula-label">综合评级</span>
              <span class="formula-eq">= 基于平均评分，规则同上</span>
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import api from '../api/index'
const { file: fileApi, predictApi, template: templateApi } = api

/**
 * 预测分析组件
 * 用于配置和执行多种预测模型，支持地区选择、模型选择和参数调整
 * 提供预测结果可视化和准确性评估
 */
export default {
  name: 'Predict',
  components: {
    InfoFilled
  },
  data() {
    return {
      selectedFileId: '',
      availableFiles: [],
      fileInfo: null,

      // 单地区配置
      selectedAreas: [],                  // 默认不选择任何地区
      selectedModels: [],                  // 默认不选择任何模型
      areaSearchKeyword: '',               // 地区搜索关键字
      modelParams: {
        stl_reg: {
          period: 144,                  // 匹配XGBoost的日周期
          degree: 2,                    
          days_window: 7               // STL适合较小窗口，快速响应
        },
        sarima: {
          order_p: 1,
          order_d: 0,
          order_q: 1,
          seasonal_P: 0,
          seasonal_D: 1,
          seasonal_Q: 0,
          seasonal_period: 144,          // 统一日周期
          days_window: 7                 // SARIMA使用7天数据
        },
        lstm: {
          sequence_length: 144,           // 序列长度（1 天）
          days_window: 7,                 // 使用最近 7 天数据
          hidden_size: 64,                // 隐藏层大小（略降容量以提速）
          num_layers: 1,                  // LSTM层数（单层更轻量）
          dropout: 0.1,                   // Dropout比率（稍强正则）
          learning_rate: 0.001,           // 学习率
          epochs: 120,                    // 训练轮数（略降）
          batch_size: 32,                 // 批次大小
          early_stopping_patience: 8,     // 早停耐心值
          bidirectional: false            // 是否双向LSTM
        },
        gru: {
          sequence_length: 144,
          days_window: 7,
          hidden_size: 64,
          num_layers: 1,
          dropout: 0.1,
          learning_rate: 0.001,
          epochs: 120,
          batch_size: 32,
          early_stopping_patience: 8,
          bidirectional: false
        },
        tcn: {
          sequence_length: 144,
          days_window: 7,
          num_filters: 64,
          kernel_size: 5,
          num_layers: 3,
          hidden_size: 96,
          dropout: 0.05,
          learning_rate: 0.001,
          epochs: 150,
          batch_size: 32,
          early_stopping_patience: 10
        },
        xgboost: {
          lag: 144,                    // 完整日周期，捕捉日模式
          n_estimators: 800,           // 进一步增加树数量
          max_depth: 8,                // 增加深度学习更复杂模式
          learning_rate: 0.03,         // 更低学习率提高稳定性
          subsample: 0.9,              // 更高子采样使用更多数据
          colsample_bytree: 0.9,      // 更高特征采样
          use_trend_features: true,
          trend_degree: 3,              // 三次趋势更灵活
          use_seasonal_features: true,
          seasonal_harmonics: 6,        // 更多谐波捕捉复杂模式
          seasonal_period: 144,        // 匹配lag的日周期
          days_window: 14              // 使用14天数据，平衡性能和稳定性
        },
        lightgbm: {
          lag: 144,
          n_estimators: 600,
          max_depth: -1,
          learning_rate: 0.03,
          subsample: 0.9,
          colsample_bytree: 0.9,
          use_trend_features: true,
          trend_degree: 3,
          use_seasonal_features: true,
          seasonal_harmonics: 6,
          seasonal_period: 144,
          days_window: 14
        },
        catboost: {
          lag: 144,
          iterations: 600,
          depth: 6,
          learning_rate: 0.03,
          use_trend_features: true,
          trend_degree: 3,
          use_seasonal_features: true,
          seasonal_harmonics: 6,
          seasonal_period: 144,
          days_window: 14
        },
        // XGBoost + 随机森林 残差混合模型参数（默认与 xgboost 相近，并为 RF 设置单独前缀参数）
        xgb_rf_residual: {
          // XGBoost 主模型参数（略降复杂度，让残差有更大发挥空间）
          lag: 96,
          n_estimators: 400,
          max_depth: 5,
          learning_rate: 0.03,
          subsample: 0.9,
          colsample_bytree: 0.9,
          use_trend_features: true,
          trend_degree: 2,
          use_seasonal_features: true,
          seasonal_harmonics: 4,
          seasonal_period: 144,
          days_window: 14,
          // 随机森林残差部分参数：更激进一些
          rf_n_estimators: 400,
          rf_max_depth: 12,
          rf_min_samples_split: 2,
          rf_min_samples_leaf: 1,
          rf_max_features: 'sqrt',
          rf_random_state: 42,
          rf_bootstrap: true,
          rf_residual_weight: 1.2
        },
        cnn: {
          sequence_length: 144,
          days_window: 7,
          num_filters: 96,
          kernel_size: 5,
          num_layers: 3,
          hidden_size: 128,
          dropout: 0.05,
          learning_rate: 0.001,
          epochs: 180,
          batch_size: 32,
          early_stopping_patience: 12
        },
        // 本地大模型预测参数
        llm_forecast: {
          model: 'gpt-oss:20b',
          temperature: 0.25,
          timeout: 300,
          days_window: 7,
          // 控制每个预测步分配的 token 数，用于推导 num_predict，默认 4
          tokens_per_step: 4
        }
      },
      singleResult: null,

      // 图表相关
      chart: null,
      selectedAreaForChart: '',
      showActual: true,
      showHistoryPred: true,
      showFuturePred: true,

      // 预测配置折叠面板：默认全部收起
      activePredictPanels: [],
      isAllAreasSelected: false,          // 默认不全选地区
      isAllModelsSelected: false,         // 默认不全选模型

      // 预测执行状态
      isPredicting: false,

      // 预测计时
      predictStartTime: null,
      elapsedSeconds: 0,
      _elapsedTimer: null,
      // 细粒度进度：当前任务序号 / 总任务数 + 当前地区/模型 + 当前任务耗时
      totalTasks: 0,
      currentTaskIndex: 0,
      currentAreaInProgress: '',
      currentModelInProgress: '',
      currentTaskStartTime: null,
      currentTaskElapsedSeconds: 0,
      // 控制：终止后续任务（仅在子任务完成后生效）
      stopRequested: false,

      // 各模型参数块折叠状态
      paramCollapsed: {
        xgboost: true,
        lightgbm: true,
        catboost: true,
        xgb_rf_residual: true,
        stl_reg: true,
        sarima: true,
        lstm: true,
        gru: true,
        cnn: true,
        tcn: true,
        llm_forecast: true
      },

      // 表格排序状态
      accuracySort: { prop: 'score', order: 'descending' },
      crossFileSort: { prop: 'score', order: 'descending' },
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
      isUsingTemplate: false
    }
  },
  computed: {
    areaColumns() {
      if (!this.fileInfo || !this.fileInfo.columns || this.fileInfo.columns.length <= 1) {
        return []
      }
      return this.fileInfo.columns.slice(1)
    },
    // 模型选项：统计 → 机器学习 → 深度学习
    modelOptions() {
      return [
        // 统计模型
        { value: 'stl_reg', label: 'STL + 线性回归' },
        { value: 'sarima', label: 'SARIMA（季节 ARIMA）' },
        // 机器学习模型
        { value: 'xgboost', label: 'XGBoost 回归' },
        { value: 'lightgbm', label: 'LightGBM 回归' },
        { value: 'catboost', label: 'CatBoost 回归' },
        { value: 'xgb_rf_residual', label: 'XGBoost + 随机森林（残差）' },
        // 深度学习模型
        { value: 'lstm', label: 'LSTM 神经网络' },
        { value: 'gru', label: 'GRU 神经网络' },
        { value: 'cnn', label: 'CNN 卷积神经网络' },
        { value: 'tcn', label: 'TCN 时间卷积网络' }
      ]
    },
    // 地区搜索过滤结果
    filteredAreaColumns() {
      const cols = this.areaColumns
      const kw = (this.areaSearchKeyword || '').trim().toLowerCase()
      if (!kw) return cols
      return cols.filter(name => String(name).toLowerCase().includes(kw))
    },
    // 当前搜索结果中的已选地区（用于标签展示和批量取消），顺序与上方复选框一致
    filteredSelectedAreas() {
      const visible = this.filteredAreaColumns
      if (!visible || visible.length === 0) return []
      const selectedSet = new Set(this.selectedAreas || [])
      // 只展示既在当前可见列表、又已被选中的地区，并保持与 filteredAreaColumns 相同的顺序
      return visible.filter(a => selectedSet.has(a))
    },
    // 是否可以执行预测（至少一个地区 + 一个模型）
    canRunPredict() {
      return !!(this.fileInfo && this.selectedAreas.length && this.selectedModels.length)
    },
    // 是否可以保存模板（需要先执行预测，获取结果）
    canSaveTemplate() {
      return !!(this.canRunPredict && this.singleResult)
    },
    // 当前选中地区下，各模型的测试集评估指标
    modelAccuracyList() {
      if (!this.singleResult || !this.selectedAreaForChart) return []
      const areaResult = this.singleResult.areas?.[this.selectedAreaForChart]
      if (!areaResult) return []

      const actual = Array.isArray(areaResult.actual) ? areaResult.actual : []
      const trainEnd = typeof areaResult.train_end_index === 'number' ? areaResult.train_end_index : 0
      const testEnd = typeof areaResult.test_end_index === 'number' ? areaResult.test_end_index : actual.length - 1
      const testStart = Math.min(trainEnd + 1, testEnd)

      // 计算测试区间真实值的平均绝对值，用于归一化 MAE
      let meanAbs = 0
      let count = 0
      for (let i = testStart; i <= testEnd && i < actual.length; i++) {
        const v = actual[i]
        if (v == null || Number.isNaN(v)) continue
        meanAbs += Math.abs(v)
        count++
      }
      if (count > 0) {
        meanAbs /= count
      }

      const eps = 1e-6
      const models = this.selectedModels
      const list = []

      models.forEach(modelKey => {
        const metrics = areaResult[`${modelKey}_metrics`]
        if (!metrics) return
        const mae = typeof metrics.mae === 'number' ? metrics.mae : NaN
        const rmse = typeof metrics.rmse === 'number' ? metrics.rmse : NaN
        if (Number.isNaN(mae) || Number.isNaN(rmse)) return

        // 组合相对 MAE 和相对 RMSE：综合相对误差 = 0.5*rel_mae + 0.5*rel_rmse
        const relMae = mae / (meanAbs + eps)
        const relRmse = rmse / (meanAbs + eps)
        const rel = 0.5 * relMae + 0.5 * relRmse
        let score = 100 / (1 + rel)
        if (score < 0) score = 0
        if (score > 100) score = 100

        let grade = '中'
        if (score >= 90) grade = '优'
        else if (score >= 80) grade = '良'
        else if (score < 60) grade = '差'

        list.push({
          modelKey,
          modelName: this.getModelName(modelKey),
          mae,
          rmse,
          score,
          grade
        })
      })

      return list
    },
    // 同一模型在当前文件所有已预测地区的平均表现（跨文件均分）
    modelCrossFileAverageList() {
      if (!this.singleResult || !this.singleResult.areas) return []
      const areas = Object.keys(this.singleResult.areas)
      if (areas.length === 0) return []

      const models = this.selectedModels
      const result = []

      models.forEach(modelKey => {
        let maeSum = 0, rmseSum = 0, scoreSum = 0, count = 0

        areas.forEach(areaKey => {
          const areaResult = this.singleResult.areas[areaKey]
          if (!areaResult) return
          const metrics = areaResult[`${modelKey}_metrics`]
          if (!metrics || typeof metrics.mae !== 'number' || typeof metrics.rmse !== 'number') return

          // 计算该地区该模型的 score（复用和单个地区相同的相对 MAE 公式）
          const actual = Array.isArray(areaResult.actual) ? areaResult.actual : []
          const trainEnd = typeof areaResult.train_end_index === 'number' ? areaResult.train_end_index : 0
          const testEnd = typeof areaResult.test_end_index === 'number' ? areaResult.test_end_index : actual.length - 1
          const testStart = Math.min(trainEnd + 1, testEnd)

          let meanAbs = 0, cnt = 0
          for (let i = testStart; i <= testEnd && i < actual.length; i++) {
            const v = actual[i]
            if (v == null || Number.isNaN(v)) continue
            meanAbs += Math.abs(v)
            cnt++
          }
          if (cnt > 0) meanAbs /= cnt

          const eps = 1e-6
          const relMae = metrics.mae / (meanAbs + eps)
          const relRmse = metrics.rmse / (meanAbs + eps)
          const rel = 0.5 * relMae + 0.5 * relRmse
          const score = Math.min(100, Math.max(0, 100 / (1 + rel)))

          maeSum += metrics.mae
          rmseSum += metrics.rmse
          scoreSum += score
          count++
        })

        if (count === 0) return

        const avgMae = maeSum / count
        const avgRmse = rmseSum / count
        const avgScore = scoreSum / count

        let grade = '中'
        if (avgScore >= 90) grade = '优'
        else if (avgScore >= 80) grade = '良'
        else if (avgScore < 60) grade = '差'

        result.push({
          modelKey,
          modelName: this.getModelName(modelKey),
          mae: avgMae,
          rmse: avgRmse,
          score: avgScore,
          grade
        })
      })

      return result
    },
    // 当前地区评估表的排序后数据
    modelAccuracyListSorted() {
      const list = [...this.modelAccuracyList]
      const { prop, order } = this.accuracySort
      if (!prop || !order) return list
      return list.sort((a, b) => {
        const av = a[prop]
        const bv = b[prop]
        if (typeof av === 'string') {
          return order === 'ascending' ? av.localeCompare(bv) : bv.localeCompare(av)
        }
        return order === 'ascending' ? av - bv : bv - av
      })
    },
    // 跨文件平均分表的排序后数据
    modelCrossFileAverageListSorted() {
      const list = [...this.modelCrossFileAverageList]
      const { prop, order } = this.crossFileSort
      if (!prop || !order) return list
      return list.sort((a, b) => {
        const av = a[prop]
        const bv = b[prop]
        if (typeof av === 'string') {
          return order === 'ascending' ? av.localeCompare(bv) : bv.localeCompare(av)
        }
        return order === 'ascending' ? av - bv : bv - av
      })
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
          
          // 处理数组长度排序
          if (Array.isArray(aVal) && Array.isArray(bVal)) {
            return order === 'ascending' ? aVal.length - bVal.length : bVal.length - aVal.length
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
    }
  },
  watch: {
    areaSearchKeyword() {
      // 搜索关键字变化时，根据当前过滤结果刷新“全选”状态
      const visibleAreas = this.filteredAreaColumns
      if (!visibleAreas || visibleAreas.length === 0) {
        this.isAllAreasSelected = false
        return
      }
      const set = new Set(this.selectedAreas)
      this.isAllAreasSelected = visibleAreas.every(a => set.has(a))
    }
  },
  async mounted() {
    await this.loadAvailableFiles()
    this.loadHistoryTemplates()
  },
  methods: {
    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    },
    formatDateTime(timestamp) {
      return new Date(timestamp).toLocaleString('zh-CN')
    },
    async loadAvailableFiles() {
      try {
        const response = await fileApi.getFileList(1, 100)
        if (response.success) {
          this.availableFiles = response.data.files || []
        }
      } catch (error) {
        ElMessage.error('加载文件列表失败')
        console.error('加载文件列表失败:', error)
      }
    },
    async loadFileInfo() {
      if (!this.selectedFileId) return
      
      try {
        // 获取文件预览以获取列信息
        const response = await fileApi.previewFile(this.selectedFileId, 1, 50)
        if (response.success) {
          this.fileInfo = {
            ...response.data.file_info,
            row_count: response.data.total_rows,
            column_count: response.data.columns?.length || 0,
            columns: response.data.columns || []
          }
          // 不默认选择地区列，让用户手动选择
          if (this.fileInfo.columns && this.fileInfo.columns.length > 1) {
            this.selectedAreas = []  // 默认不选择任何地区
            this.isAllAreasSelected = false
          }

          // 加载新文件时，重置上一批预测/图表状态，避免不同数据源之间互相干扰
          this.singleResult = null
          this.selectedAreaForChart = ''
          this.isPredicting = false
          this.predictStartTime = null
          this.elapsedSeconds = 0
          this.currentTaskStartTime = null
          this.currentTaskElapsedSeconds = 0
          this.totalTasks = 0
          this.currentTaskIndex = 0
          this.currentAreaInProgress = ''
          this.currentModelInProgress = ''
          this.stopRequested = false
          if (this._elapsedTimer) {
            clearInterval(this._elapsedTimer)
            this._elapsedTimer = null
          }
          if (this.chart) {
            window.removeEventListener('resize', this.handleResize)
            this.chart.dispose()
            this.chart = null
          }

          ElMessage.success('文件信息加载成功')
        }
      } catch (error) {
        ElMessage.error('加载文件信息失败')
        console.error('加载文件信息失败:', error)
      }
    },
    handleAreasSelectAll(checked) {
      const visibleAreas = this.filteredAreaColumns
      if (!visibleAreas || visibleAreas.length === 0) {
        this.isAllAreasSelected = false
        return
      }

      if (checked) {
        // 只对当前搜索结果中的地区执行全选，其它已选地区保持不变
        const set = new Set(this.selectedAreas)
        visibleAreas.forEach(a => set.add(a))
        this.selectedAreas = Array.from(set)
      } else {
        // 只对当前搜索结果中的地区取消选择，其它地区不动
        const visibleSet = new Set(visibleAreas)
        this.selectedAreas = this.selectedAreas.filter(a => !visibleSet.has(a))
      }

      // 更新“全选”状态：当前过滤列表中的地区是否都已选中
      const selectedSet = new Set(this.selectedAreas)
      this.isAllAreasSelected = visibleAreas.every(a => selectedSet.has(a))
    },
    handleAreasSelect() {
      const visibleAreas = this.filteredAreaColumns
      if (!visibleAreas || visibleAreas.length === 0) {
        this.isAllAreasSelected = false
        return
      }
      const set = new Set(this.selectedAreas)
      this.isAllAreasSelected = visibleAreas.every(a => set.has(a))
    },
    removeArea(area) {
      const idx = this.selectedAreas.indexOf(area)
      if (idx > -1) this.selectedAreas.splice(idx, 1)
      this.handleAreasSelect()
    },
    // 图表相关方法
    initChart() {
      // 立即销毁现有图表，不使用$nextTick，确保同步执行
      if (this.chart) {
        this.chart.dispose()
      }
      
      // 直接初始化图表，不使用$nextTick，确保同步执行
      this.chart = echarts.init(this.$refs.chartRef)
      window.addEventListener('resize', this.handleResize)
      
      // 设置默认配置，包括dataZoom配置，确保第一次设置图表选项时dataZoom功能可用
      const defaultOption = {
        backgroundColor: '#ffffff',
        grid: {
          left: 60,
          right: 60,
          top: 80,
          bottom: 60
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          }
        },
        legend: {
          data: [],
          top: 10,
          left: 'center',
          orient: 'horizontal',
          align: 'auto',
          width: '90%',
          itemWidth: 10,
          itemHeight: 10,
          itemGap: 12,
          textStyle: {
            color: '#374151',
            fontSize: 11,
            fontWeight: 400,
            padding: [0, 4, 0, 2]
          },
          padding: [0, 0, 0, 0],
          icon: 'circle'
        },
        xAxis: {
          type: 'time',
          axisLine: {
            lineStyle: {
              color: '#9ca3af'
            }
          },
          axisTick: {
            lineStyle: {
              color: '#9ca3af'
            }
          },
          axisLabel: {
            margin: 12,
            fontSize: 10,
            hideOverlap: true,
            formatter: function(value) {
              const d = new Date(value)
              if (isNaN(d.getTime())) return ''
              return d.toLocaleString('zh-CN', {
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
              }).replace(/\//g, '-')
            }
          }
        },
        yAxis: {
          type: 'value',
          splitLine: {
            lineStyle: {
              color: 'rgba(156,163,175,0.25)'
            }
          },
          splitArea: {
            show: true,
            areaStyle: {
              color: ['rgba(249,250,251,0.9)', 'rgba(243,244,246,0.9)']
            }
          },
          axisLabel: {
            formatter: function(value) {
              return value.toFixed(1)
            }
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
            height: 26,
            bottom: 8,
            borderRadius: 8,
            backgroundColor: '#f5f7fa',
            dataBackground: {
              lineStyle: { color: 'rgba(144,147,153,0.4)' },
              areaStyle: { color: 'rgba(144,147,153,0.18)' }
            },
            fillerColor: 'rgba(194,122,59,0.25)',
            handleSize: 14,
            handleStyle: {
              color: '#fff',
              borderWidth: 1,
              borderColor: 'var(--primary-color)'
            }
          }
        ],
        series: []
      }
      this.chart.setOption(defaultOption, true)
    },
    handleResize() {
      if (this.chart) {
        this.chart.resize()
      }
    },
    toggleChartLayer(layer) {
      if (layer === 'actual') {
        this.showActual = !this.showActual
      } else if (layer === 'history') {
        this.showHistoryPred = !this.showHistoryPred
      } else if (layer === 'future') {
        this.showFuturePred = !this.showFuturePred
      }
      this.$nextTick(() => {
        this.updateChart()
      })
    },
    updateChart() {
      if (!this.singleResult || !this.selectedAreaForChart) return
      
      // 批量预测返回的数据格式：{ filename, areas: { areaName: { model: [], timestamps: [] } } }
      let areaData
      if (this.singleResult.areas && this.singleResult.areas[this.selectedAreaForChart]) {
        areaData = this.singleResult.areas[this.selectedAreaForChart]
      } else if (this.singleResult[this.selectedAreaForChart]) {
        // 兼容旧格式
        areaData = this.singleResult[this.selectedAreaForChart]
      } else {
        return
      }
      
      // 如果图表未初始化，先初始化图表
      if (!this.chart) {
        this.initChart()
      }

      // 统一的颜色方案：真实值深灰，其它模型按类别分色，历史为深色实线，未来为浅色虚线
      const COLORS = {
        actual: '#111827'
      }

      const MODEL_COLORS = {
        // XGBoost：蓝色系
        xgboost: {
          history: '#2563eb',
          future: '#93c5fd'
        },
        // LightGBM：绿色系
        lightgbm: {
          history: '#16a34a',
          future: '#86efac'
        },
        // CatBoost：紫色系
        catboost: {
          history: '#7c3aed',
          future: '#c4b5fd'
        },
        // STL 回归：橙色系
        stl_reg: {
          history: '#f97316',
          future: '#fed7aa'
        },
        // SARIMA：红色系
        sarima: {
          history: '#dc2626',
          future: '#fecaca'
        },
        // LSTM：紫色系
        lstm: {
          history: '#7c3aed',
          future: '#c4b5fd'
        },
        // GRU：绿色系
        gru: {
          history: '#16a34a',
          future: '#bbf7d0'
        },
        // XGBoost+RF 残差：青色系
        xgb_rf_residual: {
          history: '#14b8a6',
          future: '#5eead4'
        },
        // CNN：品红/粉色系，避免与青色混淆
        cnn: {
          history: '#db2777',
          future: '#f9a8d4'
        },
        // TCN：棕/金色系
        tcn: {
          history: '#b45309',
          future: '#fbbf24'
        },
        // 本地大模型：青蓝色系
        llm_forecast: {
          history: '#0EA5E9',
          future: '#7DD3FC'
        }
      }

      // 准备 x 轴时间数据
      const timestamps = areaData.timestamps || []
      if (!timestamps || timestamps.length === 0) return

      const timeData = timestamps.map(t => {
        if (typeof t === 'string') return new Date(t).getTime()
        if (t instanceof Date) return t.getTime()
        if (typeof t === 'number') return t
        return new Date(t).getTime()
      })
      
      // 若部分模型预测长度超过时间戳长度，则按最后两个时间点的间隔向后外推时间轴，避免未来预测被截断
      let totalLen = timeData.length
      if (totalLen === 0) return
      let maxModelLen = 0
      Object.keys(areaData).forEach(key => {
        if (['timestamps', 'actual', 'train_end_index', 'test_end_index'].includes(key)) return
        const arr = Array.isArray(areaData[key]) ? areaData[key] : []
        if (arr.length > maxModelLen) maxModelLen = arr.length
      })
      if (maxModelLen > totalLen && totalLen >= 2) {
        const step = Math.max(1, timeData[totalLen - 1] - timeData[totalLen - 2])
        for (let i = totalLen; i < maxModelLen; i++) {
          const last = timeData[timeData.length - 1]
          timeData.push(last + step)
        }
        totalLen = timeData.length
      }

      // 训练 / 测试 / 未来 区间索引
      let trainEndIndex = typeof areaData.train_end_index === 'number' ? areaData.train_end_index : 0
      let testEndIndex = typeof areaData.test_end_index === 'number' ? areaData.test_end_index : totalLen - 1

      trainEndIndex = Math.max(0, Math.min(trainEndIndex, totalLen - 1))
      testEndIndex = Math.max(trainEndIndex, Math.min(testEndIndex, totalLen - 1))

      const futureStartIndex = Math.min(testEndIndex + 1, totalLen - 1)

      const series = []
      const legendData = []
      const historyLegendNames = []
      const futureLegendNames = []

      // 1）真实值：0 ~ testEndIndex（不在下方图例中单独展示，仅由顶部“真实值”按钮控制）
      const actual = Array.isArray(areaData.actual) ? areaData.actual : []
      const actualSeries = []
      if (actual.length > 0 && this.showActual) {
        for (let i = 0; i <= testEndIndex && i < totalLen && i < actual.length; i++) {
          const value = actual[i]
          if (value == null || Number.isNaN(value)) continue
          actualSeries.push([timeData[i], value])
        }
      }
      // 始终定义一个固定 id 的真实值 series，通过 data 是否为空来控制显隐，避免与 legend/dataZoom 产生耦合
      series.push({
        id: 'actual-series',
        name: '真实值',
        type: 'line',
        data: actualSeries,
        smooth: false,
        symbol: 'none',
        lineStyle: {
          width: 1.8,
          color: COLORS.actual
        },
        itemStyle: {
          color: COLORS.actual
        }
      })

      // 2）为每个模型分别绘制历史预测和未来预测折线
      let modelKeys = Object.keys(areaData).filter(
        key => !['timestamps', 'actual', 'train_end_index', 'test_end_index'].includes(key)
      )

      // 按类别顺序排序：统计 → 机器学习 → 深度学习
      const MODEL_ORDER = ['stl_reg', 'sarima', 'xgboost', 'lightgbm', 'catboost', 'xgb_rf_residual', 'lstm', 'gru', 'cnn', 'tcn']
      modelKeys = modelKeys.sort((a, b) => {
        const ia = MODEL_ORDER.indexOf(a)
        const ib = MODEL_ORDER.indexOf(b)
        if (ia === -1 && ib === -1) return a.localeCompare(b)
        if (ia === -1) return 1
        if (ib === -1) return -1
        return ia - ib
      })

      if (modelKeys.length === 0) {
        if (series.length === 0) return
      } else {
        modelKeys.forEach((modelKey, idx) => {
          const modelName = this.getModelName(modelKey)
          const modelData = Array.isArray(areaData[modelKey]) ? areaData[modelKey] : []

          // 为不同模型使用不同颜色
          const colorConfig = MODEL_COLORS[modelKey] || {}
          const historyColor = colorConfig.history || COLORS.history
          const futureColor = colorConfig.future || COLORS.future

          // 历史预测：0 ~ testEndIndex（始终创建 series 和 legend，显示由顶部“历史预测”按钮统一控制）
          const historySeries = []
          for (let i = 0; i <= testEndIndex && i < totalLen && i < modelData.length; i++) {
            const value = modelData[i]
            if (value == null || Number.isNaN(value)) continue
            historySeries.push([timeData[i], value])
          }
          if (historySeries.length > 0) {
            const historyName = `${modelName} 历史预测`
            legendData.push(historyName)
            historyLegendNames.push(historyName)
            series.push({
              name: historyName,
              type: 'line',
              data: historySeries,
              smooth: false,
              symbol: 'none',
              lineStyle: {
                width: 2.2,
                color: historyColor
              },
              itemStyle: {
                color: historyColor
              }
            })
          }

          // 未来预测：futureStartIndex ~ 末尾（始终创建 series 和 legend，显示由顶部“未来预测”按钮统一控制）
          const futureSeries = []
          for (let i = futureStartIndex; i < totalLen && i < modelData.length; i++) {
            const value = modelData[i]
            if (value == null || Number.isNaN(value)) continue
            futureSeries.push([timeData[i], value])
          }
          if (futureSeries.length > 0) {
            const futureName = `${modelName} 未来预测`
            legendData.push(futureName)
            futureLegendNames.push(futureName)
            series.push({
              name: futureName,
              type: 'line',
              data: futureSeries,
              smooth: false,
              symbol: 'none',
              lineStyle: {
                width: 2,
                type: 'dashed',
                color: futureColor
              },
              itemStyle: {
                color: futureColor
              }
            })
          }
        })
      }

      if (series.length === 0) return

      // 顶部“历史预测 / 未来预测”按钮作为总开关：通过 legend.selected 控制所有相关 series 的显隐
      const legendSelected = {}
      legendData.forEach(name => {
        if (historyLegendNames.includes(name)) {
          legendSelected[name] = this.showHistoryPred
        } else if (futureLegendNames.includes(name)) {
          legendSelected[name] = this.showFuturePred
        } else {
          legendSelected[name] = true
        }
      })

      // 根据图例数量粗略估计需要的高度：
      // 图例越多，占用的垂直空间越大，需要适当提高 grid.top 避免与图例交叠
      const legendCount = legendData.length || 0
      let gridTop = 80
      if (legendCount > 4 && legendCount <= 8) {
        gridTop = 95
      } else if (legendCount > 8 && legendCount <= 16) {
        gridTop = 110
      } else if (legendCount > 16) {
        gridTop = 125
      }

      const option = {
        backgroundColor: '#ffffff',
        grid: {
          left: 60,
          right: 60,
          top: gridTop, // 随图例行数变化的上边距，避免与图例交叠
          bottom: 60  // 为下方 dataZoom 滑块预留空间
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          },
          formatter: function(params) {
            if (!params || params.length === 0) return ''
            
            const time = new Date(params[0].axisValue)
            const timeStr = time.toLocaleString('zh-CN', {
              month: '2-digit',
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit'
            })
            
            let result = `时间：${timeStr}<br/>`
            params.forEach(param => {
              if (param.value && param.value.length >= 2) {
                const value = param.value[1]
                const formattedValue = typeof value === 'number' ? value.toFixed(4) : value
                result += `${param.marker} ${param.seriesName}: ${formattedValue}<br/>`
              }
            })
            return result
          }
        },
        legend: {
          // 使用普通横向图例，限制宽度让其自动换行成多排
          data: legendData,
          selected: legendSelected,
          top: 10,
          left: 'center',
          orient: 'horizontal',
          align: 'auto',
          width: '90%',
          itemWidth: 10,
          itemHeight: 10,
          itemGap: 12,
          textStyle: {
            color: '#374151',
            fontSize: 11,
            fontWeight: 400,
            padding: [0, 4, 0, 2]
          },
          padding: [0, 0, 0, 0], // 图例与图表区域之间的间距更紧凑一些
          icon: 'circle'
        },
        // 预测起点标记线：位于训练结束位置（3/4）
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: {
            color: '#909399',
            type: 'dashed',
            width: 1
          },
          label: {
            formatter: '预测起点',
            color: '#606266',
            fontSize: 12
          },
          data: [
            {
              xAxis: timeData[trainEndIndex]
            }
          ]
        },
        xAxis: {
          type: 'time',
          axisLine: {
            lineStyle: {
              color: '#9ca3af'
            }
          },
          axisTick: {
            lineStyle: {
              color: '#9ca3af'
            }
          },
          axisLabel: {
            margin: 12,
            fontSize: 10,
            hideOverlap: true,
            formatter: function(value) {
              const d = new Date(value)
              if (isNaN(d.getTime())) return ''
              return d.toLocaleString('zh-CN', {
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
              }).replace(/\//g, '-')
            }
          }
        },
        yAxis: {
          type: 'value',
          splitLine: {
            lineStyle: {
              color: 'rgba(156,163,175,0.25)'
            }
          },
          splitArea: {
            show: true,
            areaStyle: {
              color: ['rgba(249,250,251,0.9)', 'rgba(243,244,246,0.9)']
            }
          },
          axisLabel: {
            formatter: function(value) {
              return value.toFixed(1)
            }
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
            height: 26,
            bottom: 8,
            borderRadius: 8,
            backgroundColor: '#f5f7fa',
            dataBackground: {
              lineStyle: { color: 'rgba(144,147,153,0.4)' },
              areaStyle: { color: 'rgba(144,147,153,0.18)' }
            },
            fillerColor: 'rgba(194,122,59,0.25)',
            handleSize: 14,
            handleStyle: {
              color: '#fff',
              borderWidth: 1,
              borderColor: 'var(--primary-color)'
            }
          }
        ],
        series: series
      }
      
      // 使用notMerge=false，保留dataZoom等交互状态
      this.chart.setOption(option, false)
    },
    // 渲染图表基本框架，包括坐标轴、dataZoom等，不包含具体数据
    renderChartFramework() {
      // 直接调用initChart方法，它已经包含了完整的图表基本框架配置
      this.initChart()
    },
    getModelName(model) {
      const names = {
        'stl_reg': 'STL + 线性回归',
        'sarima': 'SARIMA（季节 ARIMA）',
        'lstm': 'LSTM 神经网络',
        'gru': 'GRU 神经网络',
        'xgboost': 'XGBoost 回归',
        'lightgbm': 'LightGBM 回归',
        'catboost': 'CatBoost 回归',
        'xgb_rf_residual': 'XGBoost+随机森林 残差修正',
        'cnn': 'CNN 卷积神经网络',
        'tcn': 'TCN 时间卷积网络',
        'llm_forecast': '本地大模型预测'
      }
      return names[model] || model
    },
    // 由于目前只支持ARIMA模型，简化模型选择逻辑
    handleModelsSelectAll(checked) {
      if (checked) {
        this.selectedModels = ['stl_reg', 'sarima', 'xgboost', 'lightgbm', 'catboost', 'xgb_rf_residual', 'lstm', 'gru', 'cnn', 'tcn', 'llm_forecast']
      } else {
        this.selectedModels = []
      }
      this.isAllModelsSelected = checked
    },
    handleModelsSelect() {
      const all = ['stl_reg', 'sarima', 'xgboost', 'lightgbm', 'catboost', 'xgb_rf_residual', 'lstm', 'gru', 'cnn', 'tcn', 'llm_forecast']
      this.isAllModelsSelected = all.every(m => this.selectedModels.includes(m)) && this.selectedModels.length === all.length
    },
    runPredictForSelected() {
      // 执行批量预测，获取所有选中地区和模型的结果
      if (!this.canRunPredict) return
      
      this.runBatchPredict()
    },
    async runBatchPredict() {
      if (!this.fileInfo) return
      try {
        // 每次新执行预测时，先清空上一轮的图表和结果，避免不同批次之间状态互相干扰
        this.singleResult = null
        this.selectedAreaForChart = ''
        if (this.chart) {
          window.removeEventListener('resize', this.handleResize)
          this.chart.dispose()
          this.chart = null
        }
        if (this._elapsedTimer) {
          clearInterval(this._elapsedTimer)
          this._elapsedTimer = null
        }
        this.isPredicting = false
        this.predictStartTime = null
        this.elapsedSeconds = 0
        this.currentTaskStartTime = null
        this.currentTaskElapsedSeconds = 0
        this.totalTasks = 0
        this.currentTaskIndex = 0
        this.currentAreaInProgress = ''
        this.currentModelInProgress = ''
        this.stopRequested = false

        this.isPredicting = true
        // 启动计时
        this.predictStartTime = Date.now()
        this.elapsedSeconds = 0
        this.currentTaskStartTime = null
        this.currentTaskElapsedSeconds = 0
        this.stopRequested = false
        if (this._elapsedTimer) {
          clearInterval(this._elapsedTimer)
          this._elapsedTimer = null
        }
        this._elapsedTimer = setInterval(() => {
          const now = Date.now()
          if (this.predictStartTime) {
            const diffMs = now - this.predictStartTime
            this.elapsedSeconds = Math.max(0, diffMs / 1000)
          }
          if (this.currentTaskStartTime) {
            const diffTask = now - this.currentTaskStartTime
            this.currentTaskElapsedSeconds = Math.max(0, diffTask / 1000)
          }
        }, 500)

        const filename = this.fileInfo.original_filename

        // 构造 (地区, 模型) 任务列表
        const tasks = []
        this.selectedAreas.forEach(area => {
          this.selectedModels.forEach(model => {
            tasks.push({ area, model })
          })
        })
        this.totalTasks = tasks.length
        this.currentTaskIndex = 0
        this.currentAreaInProgress = ''
        this.currentModelInProgress = ''

        // 每次新预测前清空图表选中地区，避免沿用上一次的地区 key
        this.selectedAreaForChart = ''

        // 累积结果结构，保持与批量接口一致
        this.singleResult = null

        for (let i = 0; i < tasks.length; i++) {
          const { area, model } = tasks[i]
          if (this.stopRequested) {
            break
          }
          this.currentTaskIndex = i + 1
          this.currentAreaInProgress = area
          this.currentModelInProgress = model
          this.currentTaskStartTime = Date.now()
          this.currentTaskElapsedSeconds = 0

          const payload = {
            filename,
            area_columns: [area],
            models: [model],
            model_params: this.modelParams
          }

          const resp = await predictApi.batchPredict(payload)
          if (!resp.success) {
            // 某个子任务失败，记录错误但继续后续任务
            console.error('子任务预测失败:', area, model, resp)
            continue
          }

          const part = resp.data || resp
          if (!this.singleResult) {
            this.singleResult = {
              filename: part.filename || filename,
              areas: {},
              models: this.selectedModels,
              timestamp: part.timestamp || new Date().toISOString()
            }
          }

          const areas = part.areas || {}
          Object.keys(areas).forEach(areaName => {
            const areaResult = areas[areaName]
            if (!this.singleResult.areas[areaName]) {
              this.singleResult.areas[areaName] = areaResult
            } else {
              Object.assign(this.singleResult.areas[areaName], areaResult)
            }
          })

          // 不自动设置默认地区，让用户手动选择
          // 不自动初始化和更新图表，只有当用户选择地区后才显示
        }

        // 不自动切换地区和刷新图表，让用户手动选择地区后才显示
        // 清空之前的选中地区，确保用户必须手动选择
        this.selectedAreaForChart = ''
        
        // 渲染图表基本框架，包括坐标轴、dataZoom等，这样第一次选择地区时，dataZoom功能就可以正常使用
        this.$nextTick(() => {
          this.renderChartFramework()
        })

        // 根据是否被用户中途终止，给出真实的提示信息
        if (this.stopRequested) {
          ElMessage.warning(`预测已终止：共 ${this.totalTasks} 个子任务，已完成 ${this.currentTaskIndex} 个`)
        } else {
          ElMessage.success(`批量预测完成：${this.selectedAreas.length}个地区，${this.selectedModels.length}个模型（${this.totalTasks} 个子任务）`)
        }
      } catch (error) {
        ElMessage.error(error.message || '批量预测失败')
        console.error('批量预测失败:', error)
      } finally {
        this.isPredicting = false
        if (this._elapsedTimer) {
          clearInterval(this._elapsedTimer)
          this._elapsedTimer = null
        }
        this.totalTasks = 0
        this.currentTaskIndex = 0
        this.currentAreaInProgress = ''
        this.currentModelInProgress = ''
        this.currentTaskStartTime = null
        this.currentTaskElapsedSeconds = 0
        this.stopRequested = false
      }
    },
    requestStop() {
      if (!this.isPredicting) return
      this.stopRequested = true
    },
    resetPredictConfig() {
      // 重置为初始状态：清空文件选择、重置配置、清空结果
      this.selectedFileId = ''
      this.fileInfo = null
      this.selectedAreas = []
      this.isAllAreasSelected = false
      this.selectedModels = []
      this.isAllModelsSelected = false
      this.activePredictPanels = []
      this.isAllModelsSelected = false
      this.singleResult = null
      this.selectedAreaForChart = ''
      this.predictStartTime = null
      this.elapsedSeconds = 0
      ElMessage.success('预测配置已重置')
    },
    formatNumber(val) {
      if (val === null || val === undefined || Number.isNaN(val)) return '-'
      return Number(val).toFixed(4)
    },
    formatSeconds(sec) {
      if (!sec || sec <= 0) return '0s'
      const total = Math.floor(sec)
      const m = Math.floor(total / 60)
      const s = total % 60
      if (m <= 0) return `${s}s`
      return `${m}m ${s}s`
    },
    // 当前地区评估表排序事件
    handleAccuracySortChange({ prop, order }) {
      this.accuracySort = { prop, order }
    },
    // 跨文件平均分表排序事件
    handleCrossFileSortChange({ prop, order }) {
      this.crossFileSort = { prop, order }
    },
    removeModel(model) {
      this.selectedModels = this.selectedModels.filter(m => m !== model)
      // 标签删除时也要刷新全选状态
      this.handleModelsSelect()
    },
    toggleParamCollapse(modelKey) {
      if (!this.paramCollapsed || !(modelKey in this.paramCollapsed)) return
      this.paramCollapsed[modelKey] = !this.paramCollapsed[modelKey]
    },
    // 加载历史模板
    async loadHistoryTemplates() {
      try {
        const response = await templateApi.getTemplates('predict')
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
        ElMessage.error('模板名称已存在，请更改模板名称')
        return
      }
      
      // 检查是否有结果可以保存
      if (!this.singleResult) {
        ElMessage.warning('请先执行预测分析，获取结果后再保存模板')
        return
      }
      
      const templateData = {
        name: templateName,
        type: 'predict',
        config: {
          fileId: this.selectedFileId,
          areas: [...this.selectedAreas],
          models: [...this.selectedModels],
          modelParams: JSON.parse(JSON.stringify(this.modelParams))
        },
        results: {
          // 只保存必要的结果信息，不保存完整的预测结果
          selectedAreaForChart: this.selectedAreaForChart,
          showActual: this.showActual,
          showHistoryPred: this.showHistoryPred,
          showFuturePred: this.showFuturePred,
          // 保存模板创建时的原文件ID和名称，用于加载时检查
          originalFile: {
            id: this.selectedFileId,
            name: this.fileInfo?.original_filename || this.selectedFileId
          }
        }
      }
      
      try {
        await templateApi.createTemplate(templateData)
        ElMessage.success('模板保存成功，包含分析结果')
        // 重新加载模板列表
        this.loadHistoryTemplates()
      } catch (error) {
        console.error('保存模板失败:', error)
        ElMessage.error('保存模板失败，请重试')
      }
    },
    // 加载模板
    async loadTemplate(template) {
      if (!template) return
      
      // 检查模板创建时的原文件是否存在
      const originalFile = template.results?.originalFile
      if (originalFile) {
        try {
          // 尝试加载文件信息
          await this.loadFileInfo(originalFile.id)
          // 原文件存在，自动加载
          this.selectedFileId = originalFile.id
          // 设置使用模板标志，禁用地区选择
          this.isUsingTemplate = true
        } catch (error) {
          // 原文件不存在，给出明确的提示
          console.error('原文件不存在，无法加载:', error)
          ElMessage.error(`原文件 ${originalFile.name} 已被删除，无法加载`)
        }
      } else if (template.config.fileId) {
        // 尝试从配置中获取文件ID
        try {
          await this.loadFileInfo(template.config.fileId)
          this.selectedFileId = template.config.fileId
          this.isUsingTemplate = true
        } catch (error) {
          console.error('加载文件信息失败:', error)
          ElMessage.error('无法加载模板对应的文件')
        }
      }
      
      // 加载模板配置
      this.selectedAreas = [...template.config.areas]
      this.selectedModels = [...template.config.models]
      this.modelParams = JSON.parse(JSON.stringify(template.config.modelParams))
      
      // 如果模板包含结果数据，直接加载结果，不需要重新计算
      if (template.results) {
        this.singleResult = JSON.parse(JSON.stringify(template.results.singleResult))
        // 不自动设置选中地区，让用户手动选择
        this.selectedAreaForChart = ''
        this.showActual = template.results.showActual
        this.showHistoryPred = template.results.showHistoryPred
        this.showFuturePred = template.results.showFuturePred
        
        // 渲染图表基本框架，包括坐标轴、dataZoom等，这样第一次选择地区时，dataZoom功能就可以正常使用
        // 确保图表完全空白，没有任何之前的数据残留
        this.$nextTick(() => {
          this.renderChartFramework()
        })
        
        ElMessage.success('模板加载成功，请选择地区查看分析结果')
      } else {
        ElMessage.success('模板加载成功，请点击执行按钮进行分析')
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
        ElMessage.success('模板删除成功')
        // 重新加载模板列表
        this.loadHistoryTemplates()
      } catch (error) {
        console.error('删除模板失败:', error)
        ElMessage.error('删除模板失败，请重试')
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
  },
  beforeUnmount() {
    if (this.chart) {
      window.removeEventListener('resize', this.handleResize)
      this.chart.dispose()
      this.chart = null
    }
    if (this._elapsedTimer) {
      clearInterval(this._elapsedTimer)
      this._elapsedTimer = null
    }
  }
}
</script>

<style scoped>
.predict-container {
  padding: 20px;
}

.predict-container h1 {
  font-size: 24px;
  margin-bottom: 30px;
  color: #303133;
  font-weight: 600;
}

.predict-container h1 {
  font-weight: 600;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
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

.mb-4 {
  margin-bottom: 1rem;
}

.accuracy-wrapper {
  padding: 12px 20px 16px 20px;
}

.accuracy-empty {
  padding: 8px 0;
  font-size: 13px;
  color: #6b7280;
}

.accuracy-details {
  padding: 8px 12px;
  margin-top: 8px;
}

.rule-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.rule-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.rule-text {
  font-size: 13px;
  color: #374151;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.formula-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 32px; /* 行间距略大、左右列间距更大一些 */
  align-items: baseline;
}

.formula-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: nowrap;  /* 尽量不在一条公式内换行 */
}

.formula-label {
  font-weight: 600;
  color: #111827;
  min-width: 80px;
  font-size: 13px;
}

.formula-eq {
  white-space: nowrap;       /* 尽量保持等式在一行 */
}

.formula-eq {
  font-family: 'Consolas', 'Monaco', monospace;
  color: #1f2937;
  font-size: 13px;
}

.formula-note {
  color: #6b7280;
  font-size: 12px;
  font-style: italic;
}

.metric-number {
  font-family: 'Consolas', 'Monaco', monospace;
  font-weight: 500;
  color: #374151;
}

.score-number {
  font-weight: 600;
  color: #111827;
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

.chart-toggle-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-toggle-btn {
  border-radius: 8px;
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.12);
  color: #374151;
  padding: 4px 12px;
  font-size: 13px;
}

.chart-toggle-btn-active {
  border-color: #2563eb;
  color: #1d4ed8;
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.35);
}

.option-content {
  display: flex;
  flex-direction: column;
}

.text-gray-500 {
  color: #606266;
  font-size: 12px;
}

.feature-selection-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.select-all-container {
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.feature-list {
  max-height: 220px;
  overflow-y: auto;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background-color: var(--page-inner-bg);
}

.model-category {
  margin-bottom: 12px;
}

.category-title {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin-right: 8px;
}

.selection-label {
  font-size: 13px;
  color: #4b5563;
  margin-right: 8px;
}

/* 预测分析页面的已选择项目样式 - 添加滑动条 */
.selected-features-display {
  max-height: 120px;
  overflow-y: auto;
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px 24px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.vertical-params {
  grid-template-columns: 1fr;
}

.algo-block {
  padding: 10px 12px;
  border-radius: 8px;
  background-color: color-mix(in srgb, var(--primary-color) 6%, #ffffff 94%);
  border: 1px solid color-mix(in srgb, var(--primary-color) 18%, #ffffff 82%);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}

.param-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.param-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  margin-bottom: 6px;
}

.param-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

/* 模型参数卡片右上角“展开/收起”按钮样式美化 */
.param-title-row :deep(.el-button) {
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  background: #ffffff !important;
  border: 1px solid color-mix(in srgb, var(--primary-color) 50%, #ffffff 50%) !important;
  color: var(--primary-color) !important;
  box-shadow: 0 2px 6px rgba(194, 122, 59, 0.25);
}

.param-title-row :deep(.el-button:hover) {
  background: color-mix(in srgb, var(--primary-color) 10%, #ffffff 90%) !important;
  border-color: color-mix(in srgb, var(--primary-color) 70%, #ffffff 30%) !important;
  box-shadow: 0 3px 10px rgba(194, 122, 59, 0.35);
}

.param-label {
  font-size: 13px;
  color: #4b5563;
}

.small-text {
  font-size: 12px;
}

.chart-wrapper {
  padding: 12px 20px 20px;
}

.predict-chart {
  width: 100%;
  height: 540px;
}

.predict-progress-wrapper {
  padding: 0 20px 12px 20px;
  display: flex;
  align-items: stretch;
  gap: 16px;
}

.predict-progress-left {
  flex: 1 1 auto;
}

.predict-progress-info {
  margin-top: 6px;
  font-size: 13px;
  color: #374151;
}

.progress-line {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 2px;
}

.progress-line:last-child {
  margin-bottom: 0;
}

.progress-label {
  min-width: 90px;
  font-weight: 500;
  color: #4b5563;
}

.progress-value {
  font-family: 'Consolas', 'Monaco', monospace;
  color: #111827;
}

.predict-progress-actions {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

@media screen and (max-width: 768px) {
  .predict-container {
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