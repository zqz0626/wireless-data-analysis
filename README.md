# 无线大数据分析系统（wireless-data-analysis）

无线大数据分析系统是一个面向无线业务场景的数据分析平台，提供从数据管理、预处理，到异常检测、聚类分析和预测分析的一体化流程支持。

系统采用前后端分离架构：
- 前端：Vue 3 + Vue Router + Element Plus + Vite
- 后端：FastAPI + Uvicorn + SQLAlchemy + 多种机器学习 / 深度学习库

---

## 功能概览

- **数据管理**
  - 支持 CSV / Excel 等多格式数据文件上传
  - 数据预览与基础统计分析
  - 处理前/处理后/地图文件导出
  - 数据版本管理与历史版本回溯

- **预处理配置**
  - 缺失值填补（均值/中位数等）
  - 标准化/归一化
  - 质量评估（完整性、一致性等）
  - 生成标准化结果文件，作为后续分析输入

- **异常检测**
  - Isolation Forest 无监督检测异常点
  - 对异常点支持插值修正并生成修正版数据文件
  - 提供异常分数、触发特征、严重等级等解释
  - 时间轴散点可视化，支持切换 Y 轴指标
  - 支持长耗时任务异步运行与进度查询

- **聚类分析**
  - 支持 K-Means、层次聚类、GMM 多种算法
  - 聚类数 K 估计（轮廓系数、DB 指数、Calinski-Harabasz 等）
  - 聚类分布、每簇特征统计、簇画像描述
  - 按“地区-时间序列”视角进行聚类，支持时序趋势总结

- **预测分析**
  - 基于 STL 分解 + 多项式回归的时序预测（服务实现已存在，API 暂时禁用）
  - 支持 3/4 训练 + 1/4 测试 + 1/8 未来预测
  - 输出训练/测试/未来预测曲线及误差指标（MAE/MSE/RMSE）

---

## 技术栈

- **前端**
  - Vue 3、Vue Router 4
  - Element Plus
  - Vite
  - ECharts、Leaflet、VXE-Table 等可视化组件

- **后端**
  - FastAPI + Uvicorn
  - Pydantic / pydantic-settings
  - SQLAlchemy（MySQL）
  - Requests、Pillow、psutil 等

- **数据与建模**
  - NumPy、Pandas、Statsmodels
  - Scikit-learn
  - XGBoost、LightGBM、CatBoost
  - PyTorch
  - Openpyxl（Excel 读写）

---

## 目录结构（简要）

```text
wireless-data-analysis/
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI 应用入口
│   │   ├── api/
│   │   │   └── analysis_router.py  # 异常检测 / 聚类 / 预测 API
│   │   ├── services/
│   │   │   ├── anomaly_service.py   # 异常检测服务
│   │   │   ├── cluster_service.py   # 聚类分析服务
│   │   │   ├── prediction_service.py# 预测分析服务
│   │   │   └── task_manager.py      # 长耗时任务管理
│   │   ├── models/              # ORM 模型
│   │   ├── config/              # 配置
│   │   └── middleware/          # 中间件
│   ├── uploads/                 # 上传数据与导出结果
│   └── requirements.txt         # 后端依赖
│
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   └── Home.vue         # 首页：系统功能和技术栈介绍
│   │   ├── router/              # 前端路由
│   │   └── ...                  # 其他页面与组件
│   ├── package.json
│   └── vite.config.*            # Vite 配置
│
└── check_db.py                  # 数据库检查/初始化脚本（如有）
```

---

## 环境与启动

### 后端

1. 安装依赖（在 `backend/` 目录下）：

```bash
pip install -r requirements.txt
```

2. 准备数据库（MySQL）：
   - 创建数据库和用户
   - 在 `backend/app/config` 中通过环境变量或配置文件设置连接串  
   - 首次启动时，`main.py` 中的 `Base.metadata.create_all(bind=engine)` 会自动建表

3. 启动后端服务：

```bash
cd backend
python -m app.main          # 默认 8000 端口
# 或
python -m app.main --port 8000
```

- 健康检查：`GET /health`
- 根路径：`GET /` 返回简单 JSON
- 上传/导出静态文件：`/uploads`、`/api/uploads` 指向 `backend/uploads/`

### 前端

1. 在 `frontend/` 目录下安装依赖：

```bash
npm install   # 或 pnpm install / yarn install
```

2. 启动开发服务器：

```bash
npm run dev
```

3. 构建与预览：

```bash
npm run build
npm run preview
```

---

## 算法实现与参数说明

### 1. 异常检测（Isolation Forest）

核心实现：`backend/app/services/anomaly_service.py::AnomalyDetectionService.detect_isolation_forest`

#### 1.1 基本思想

- 使用 `IsolationForest` 对多维数值特征进行无监督异常检测。
- 代码中**按列建模**：对每个数值特征分别训练一个 Isolation Forest，再把各列的异常结果合并：
  - 某一行在任何一列被判为异常，就视为整体异常；
  - 异常分数取各列归一化后得分的最大值；
  - 记录触发异常的特征列表（`trigger_features_map`）。

#### 1.2 接口与参数（API）

接口路径：`POST /api/analysis/anomaly`

关键参数（请求体 `Body`）：

- **`file_id: str`**
  - 上传文件的 ID，通过文件管理模块获取。
- **`method: str`**
  - 当前仅支持 `"isolation_forest"`，否则报错。
- **`features: List[str]`**
  - 参与检测的特征列名列表。
  - 如果为空或不传，则自动选取所有数值列。
- **`contamination: float`**
  - 预期异常样本比例，默认 `0.1`。  
  - 用于控制内部阈值（分位数），范围被安全截断在 `[1e-6, 0.5]`。
- **`n_estimators: int`**
  - 森林中树的数量，默认 `100`。
  - 大数据集时会自动下调以控制时间（当样本数非常大时）。
- **`max_samples: Union["auto", int]`**
  - 单棵树使用的样本数。
  - `'auto'`：代码内设为 `min(256, n_samples)`，避免一次性加载太多样本。
  - `int`：会截断到 `[1, n_samples]`。
- **`y_axis_feature: Optional[str]`**
  - 用于前端散点图 Y 轴展示和插值修正的目标列。
  - 不限制检测维度，只影响修正和可视化。
- （异步版本）`task_id` 内部使用，用于更新任务进度。

#### 1.3 数据预处理逻辑

见 `_prepare_data` ：

- 选择目标特征列：如果提供 `features`，会过滤掉不存在的列；否则自动选取所有数值列。
- 尝试用 `pd.to_numeric` 强制转换；转换失败的列会被丢弃。
- 替换正/负无穷大为 `NaN`。
- 先用中位数填补，再对整列全为 NaN 的情况二次用 0 填补。
- 使用 `StandardScaler` 标准化到零均值单位方差。
- 样本数不足 2 会直接报错。

#### 1.4 结果与解释

`detect_isolation_forest` 返回的主要字段（由 `_format_results` 生成）包括：

- **`anomaly_count`**：检测到的异常样本数量。
- **`scores`**：每条样本的异常得分（0~1，越大越异常）。
- **`anomaly_indices`**：异常样本的行索引列表。
- **`trigger_features`**：对每个异常样本，触发异常的特征列名列表。
- **`severity`**：可根据得分分为高/中/低（由前后端约定阈值）。
- **`corrected_file`**：
  - `path`: 修正后文件路径；
  - `filename`: 修正后文件名。
- 散点图数据和时间轴信息，用于前端可视化。

#### 1.5 异步任务模式

- 提交任务：`POST /api/analysis/anomaly/task`
  - 参数与同步接口基本一致。
  - 返回 `task_id` 用于轮询。
- 查询任务：`GET /api/analysis/anomaly/task/{task_id}`
  - 使用 `TaskManager` 维护任务状态：
    - `pending / running / finished / failed`
  - 任务运行过程中，`detect_isolation_forest` 会按“特征列进度”更新 `progress`。

---

### 2. 聚类分析

核心实现：`backend/app/services/cluster_service.py::ClusterService`

#### 2.1 数据视角

本系统的聚类主要是**按地区的时间序列进行分群**：

- 视每一个“地区列”为一个样本；
- 整条时间序列（多时间点值）为该样本的特征向量；
- 通过 `_prepare_region_data` 实现：
  - 原始数据列为各地区，行索引为时间；
  - 转置后 `X`: 行为地区，列为 `t_0, t_1, ..., t_n`。

这样可以根据各地区在一段时间内的整体走势与水平进行分群，并后续结合时间趋势做解释。

#### 2.2 公共预处理参数

在 `/cluster` 相关接口和服务函数中，有以下公共参数：

- **`file_id: str`**
  - 选取的预处理后数据文件 ID。
- **`features: List[str]`**
  - 地区或其他需要聚类的列名。
  - 若为空，则默认使用所有数值列。
- **`standardize: bool`**
  - 是否对特征进行标准化（`StandardScaler`）。
  - 开启后，各地区序列会按列进行零均值单位方差变换。
- **`dimensionality_reduction: str`**
  - 降维方法：
    - `"none"`：不降维；
    - `"pca"`：使用主成分分析。
- **`pca_components: int`**
  - PCA 降维后的维度数，自动截断到不超过原始列数。

#### 2.3 K-Means 聚类

实现：`ClusterService.kmeans_clustering`

接口：`POST /api/analysis/cluster`，`algorithm="kmeans"`

参数：

- **`n_clusters: int`**
  - 聚类数 K，默认 `3`。
- **`max_iter: int`**
  - 最大迭代次数，默认 `300`。
- **`random_state: int`**
  - 随机种子，保证结果可复现。
- 以及前述的 `features, standardize, dimensionality_reduction, pca_components`。

输出核心字段：

- `labels`：每个地区所属的聚类标签（0, 1, 2, ...）。
- `cluster_centers`：聚类中心（在降维前特征空间中的中心，若未降维）。
- `inertia`：簇内平方和，用于“肘部法则”观察聚类紧致度。
- `silhouette_score`：轮廓系数，[-1, 1]，越大越好。
- `davies_bouldin_score`：DB 指数，越小越好。
- `calinski_harabasz_score`：CH 指数，越大越好。
- `cluster_distribution`：详细的每簇统计信息（见 2.6）。
- `time_trends`：按簇聚合后的时间序列趋势数据，便于前端绘制簇趋势图。
- `cluster_comments`：按簇生成的自然语言摘要（峰值时间、成员数量等）。

#### 2.4 层次聚类

实现：`ClusterService.hierarchical_clustering`

接口：`algorithm="hierarchical"`

特有参数：

- **`linkage: str`**
  - 连接方式，默认 `"ward"`，可选 `'ward', 'complete', 'average', 'single'` 等。
  - 控制聚类树中簇之间距离的度量方式。

输出与 K-Means 类似（不包含质心坐标和迭代次数）。

#### 2.5 高斯混合模型（GMM）

实现：`ClusterService.gmm_clustering`

接口：`algorithm="gmm"`

特有参数：

- **`covariance_type: str`**
  - 协方差类型，默认 `"full"`。
  - 可选：`"full"`, `"tied"`, `"diag"`, `"spherical"`，用于控制簇形状灵活度与复杂度平衡。

输出除常规聚类指标外，还包括：

- `bic`：贝叶斯信息准则（BIC），越小越好。
- `aic`：AIC，越小越好。
- `converged`：是否收敛。

#### 2.6 聚类分布与特征画像

由 `_generate_cluster_distribution`, `_extract_top_feature_differences` 等函数实现，输出字段包括：

- **`cluster_id`**：簇编号。
- **`size` / `percentage`**：簇中样本数及占比。
- **`center`**：该簇在各特征维度上的均值（簇中心）。
- **`feature_stats`**：每个特征在该簇中的均值、标准差、最小值和最大值。
- **`top_features`**：
  - 与整体均值相比变化幅度最大的若干特征（默认前 3 个）；
  - 包含 `delta`（高于/低于整体的差值）信息。
- **`summary`**：
  - 形如“聚类 1: 特征A 高于整体 x.xx，特征B 低于整体 y.yy”的中文描述。

这些信息便于前端做簇画像（如雷达图、标签化描述等）。

#### 2.7 K 值估计

实现：`ClusterService.estimate_optimal_k`

接口：`POST /api/analysis/cluster/estimate-k`

关键参数：

- **`k_min, k_max`**
  - K 的搜索范围，默认 `[2, 10]`。
- **`standardize`**：是否在估计过程中标准化。

内部逻辑：

- 对 `k_min...k_max` 所有 K 值分别跑一次 K-Means；
- 记录每个 K 对应的：
  - `inertia`
  - `silhouette_score`
  - `davies_bouldin_score`
  - `calinski_harabasz_score`
- 按轮廓系数最大值选出推荐的 `best_k`，并在结果中标记 `is_recommended=True`。

#### 2.8 在系统中如何运行聚类分析

- **前端运行步骤（聚类分析模块）**：
  1. 在首页或导航中进入“聚类分析”模块；
  2. 在左侧/顶部选择一个已经预处理过的文件（通常是经过“预处理配置”生成的文件）；
  3. 在特征选择区域勾选需要进行聚类的列（通常是各地区或业务指标列）；
  4. 需要时先在“K 值估计”面板中配置 `k_min` / `k_max` 与 `standardize`，点击运行，参考返回的推荐 K 值；
  5. 在聚类配置面板中选择：
     - `algorithm`：`kmeans` / `hierarchical` / `gmm`；
     - 对应算法特定参数（如 K-Means 的 `n_clusters`、`max_iter`，层次聚类的 `linkage`，GMM 的 `covariance_type` 等）；
     - 是否 `standardize` 以及是否启用 `pca` 降维和 `pca_components`；
  6. 点击“开始聚类分析”，前端会调用后端 `/api/analysis/cluster` 接口并在完成后展示：
     - 每个对象（地区）的聚类标签；
     - 各聚类在地图、散点或表格中的分布；
     - 评估指标（轮廓系数、DB、CH 等）和“簇画像”文字描述；
     - 各簇时间趋势曲线，便于比较不同簇在时间上的整体走势。

- **后端接口对应关系**：
  - 估计 K 值时：前端调用 `POST /api/analysis/cluster/estimate-k`，传入 `file_id`、`features`、`k_min`、`k_max`、`standardize`；
  - 正式聚类时：前端调用 `POST /api/analysis/cluster`，传入 `file_id`、`algorithm`、`features` 以及对应算法参数；
  - 后端会将 `ClusterService` 返回的 `labels`、`cluster_distribution`、`time_trends`、`cluster_comments` 等字段直接返回前端，用于可视化和结果解释。

---

### 3. 预测分析

核心实现：`backend/app/services/prediction_service.py::PredictionService`

> 说明：历史接口 `/api/analysis/predict` 已移除，当前实际使用的预测接口为：
> - `POST /api/predict/stl-reg`：单地区 STL + 回归预测；
> - `POST /api/predict/batch-predict`：多地区、多模型的批量预测接口，内部调用 `PredictionService` 中的十种预测模型实现。

#### 3.0 模型列表与适用场景

在批量预测接口 `batch_predict_by_areas` 中，系统支持以下十种预测模型（通过 `models` 参数选择）：

- **stl_reg**（STL + 回归）
  - **实现**：`sarima_timeseries_prediction`（内部用 STL 分解 + 多项式回归）；
  - **适用**：有明显趋势和季节性、且希望模型可解释的场景；
  - **关键参数（`stl_reg_params`）**：`period`（季节周期）、`days_window`（窗口长度）、`degree`（趋势多项式阶数）、`robust`（鲁棒分解）。

- **sarima**（SARIMAX 季节 ARIMA）
  - **实现**：`sarimax_timeseries_prediction`；
  - **适用**：平稳性较好、季节性明确的经典时间序列；
  - **关键参数（`sarima_params`）**：`seasonal_period`、`order_p/d/q`、`seasonal_P/D/Q` 或整体 `order` / `seasonal_order`、`days_window`。

- **xgboost**（梯度提升树回归）
  - **实现**：`xgboost_timeseries_prediction`；
  - **适用**：非线性关系强、特征较多的时序回归；
  - **特征**：滞后窗口 + 统计特征 + 趋势特征 + 正弦/余弦季节特征；
  - **关键参数（`xgb_params`）**：`lag`、`seasonal_period`、`days_window`、`use_seasonal_features`、`seasonal_harmonics`、`use_trend_features`、`trend_degree`、`n_estimators`、`max_depth`、`learning_rate`、`subsample`、`colsample_bytree`。

- **lightgbm**（LightGBM 回归）
  - **实现**：`lightgbm_timeseries_prediction`；
  - **适用**：与 XGBoost 类似，偏向更快的树模型；
  - **特征**：与 XGBoost 完全一致，便于对比不同树模型；
  - **关键参数（`lgbm_params`）**：与 XGBoost 对应的 `lag/seasonal_period/days_window/use_*` 等 + `n_estimators`、`max_depth`、`learning_rate`、`subsample`、`colsample_bytree`。

- **catboost**（CatBoost 回归）
  - **实现**：`catboost_timeseries_prediction`；
  - **适用**：与 XGBoost/LightGBM 类似，但对某些分布更鲁棒；
  - **特征**：与 XGBoost 模型保持一致；
  - **关键参数（`cat_params`）**：`lag`、`seasonal_period`、`days_window`、`use_*` 类参数，以及 `iterations`、`depth`、`learning_rate` 等。

- **xgb_rf_residual**（XGBoost + 随机森林残差）
  - **实现**：`xgb_rf_residual_timeseries_prediction`；
  - **适用**：希望在 XGBoost 的基础上进一步拟合复杂残差结构的场景；
  - **机制**：先用 XGBoost 拟合主序列，再用 RandomForest 回归拟合残差并加权叠加；
  - **关键参数（`hybrid_params`）**：与 XGBoost 相同的基础参数 + RF 相关参数如 `rf_n_estimators`、`rf_max_depth`、`rf_min_samples_split`、`rf_min_samples_leaf`、`rf_max_features`、`rf_residual_weight` 等。

- **lstm**（LSTM 深度时序网络）
  - **实现**：`lstm_timeseries_prediction`（PyTorch）；
  - **适用**：长序列、复杂非线性依赖关系强的场景；
  - **关键参数（`lstm_params`）**：`sequence_length`（输入序列长度）、`days_window`、`hidden_size`、`num_layers`、`dropout`、`learning_rate`、`epochs`、`batch_size`、`early_stopping_patience`、`bidirectional`。

- **gru**（GRU 深度时序网络）
  - **实现**：`gru_timeseries_prediction`；
  - **适用**：与 LSTM 类似，但参数更少，训练更快；
  - **关键参数（`gru_params`）**：整体与 LSTM 类似，包括 `sequence_length`、`hidden_size`、`num_layers`、`dropout`、`learning_rate`、`epochs` 等。

- **cnn**（一维卷积网络）
  - **实现**：`cnn_timeseries_prediction`；
  - **适用**：对局部时间模式敏感的场景（如短期波动、局部峰值）；
  - **关键参数（`cnn_params`）**：`sequence_length`、卷积层通道数/卷积核大小/步长（在实现中封装）以及学习率、epoch 等训练超参。

- **tcn**（Temporal Convolutional Network）
  - **实现**：`tcn_timeseries_prediction`；
  - **适用**：需要在卷积结构中捕获较长依赖关系的时序任务；
  - **关键参数（`tcn_params`）**：`sequence_length`、层数、扩张系数、卷积核大小、残差结构相关参数，以及学习率/epoch 等训练超参。

在前端“预测分析”模块中，可以将上述模型名称与可选项一一对应，批量预测时通过 `models` 列表传入需要对比的一组模型，并通过 `model_params` 为不同模型分别配置参数。

#### 3.1 数据加载与切分

- `_load_timeseries(filename, area_column)`：
  - 从 `uploads/` 目录加载 CSV；
  - 第一列作为时间索引（自动转为 `datetime` 并排序）；
  - `area_column` 为指定地区列；
  - 删除无穷值与 NaN，得到一个单一时间序列。

- `_train_test_future_split(series)`：
  - 序列长度为 `n` 时：
    - 训练集长度 `≈ 0.75 n`
    - 测试集长度 `≈ 0.25 n`
    - 未来预测步数 `future_steps = max(1, n//8)`（即约 1/8 长度）

#### 3.2 STL + 多项式回归

实现：`sarima_timeseries_prediction`（命名中有 sarima，但实际为 STL + 回归）

主要步骤：

1. **可选窗口截断**
   - 参数 `stl_reg_params` 中：
     - `days_window`：>0 时，仅保留最近 `days_window * period` 个点建模；
     - `period`：一个周期长度（默认约 140，假定对应 10 分钟粒度的日周期）。
2. **时序分解**
   - 使用 `statsmodels.tsa.seasonal.STL`：
     - `period`：季节周期长度；
     - `robust`：是否使用鲁棒回归，默认 True。
   - 得到趋势项 `trend_train` 和季节项 `seasonal_train`。
3. **趋势拟合**
   - 使用 `LinearRegression` 对趋势项做 1~3 阶多项式回归：
     - `degree` ∈ [1,3]，超出范围会被截断。
     - 自变量为时间步索引 `t = 0,1,...`。
   - 在“训练 + 测试 + 未来”全区间上预测趋势 `trend_all_pred`。
4. **季节项扩展**
   - 将训练集中的季节项最后一个周期片段循环平铺到整个区间，得到 `seasonal_all`。
5. **合成预测**
   - `y_all_pred = trend_all_pred + seasonal_all`；
   - 从中切出测试区间预测 `test_pred` 和未来预测 `future_forecast`。
6. **误差指标**
   - 基于测试集真实值与 `test_pred` 计算：
     - MAE
     - MSE
     - RMSE

关键参数（`stl_reg_params` 字典）：

- **`period` (int)**  
  - 季节周期长度，控制 STL 分解的季节成分；
  - 对于 10 分钟粒度、日周期数据，可设置为 144 左右（具体由数据粒度决定）。
- **`days_window` (int)**  
  - 仅使用最近多少天的数据建模。  
  - `0` 或不传：使用全部历史数据；
  - >0：使用最近 `days_window * period` 个点。
- **`degree` (int)**  
  - 趋势回归的多项式阶数，1~3：
    - 1 阶：线性趋势；
    - 2 阶：二次曲线，可表达“先升后降”等；
    - 3 阶：更复杂的非线性趋势。
- **`robust` (bool)**  
  - STL 是否启用鲁棒拟合，以减弱异常点对周期分解的影响。

输出结果字段：

- `history_index/history_values`：完整历史序列；
- `train_index/train_values`：训练集；
- `test_index/test_values/test_pred_values`：测试集及预测；
- `future_index/future_forecast_values`：未来预测曲线；
- `metrics`：MAE/MSE/RMSE。

#### 3.3 在系统中如何运行预测分析

> 当前在线接口 `/api/analysis/predict` 返回“预测功能已禁用”，下面说明的是基于 `PredictionService` 的典型运行流程，便于后续启用或在脚本中复用。

- **前端/业务侧配置**（建议方案）：
  - 选择输入文件：从“数据管理”或“预处理配置”模块中，选定某个已经上传并完成预处理的 CSV 文件；
  - 选择地区列：在前端界面中选择一个地区列（如某个区域的流量序列），作为 `area_column`；
  - 设置预测参数：
    - `period`：一个季节周期长度（例如 144 表示 10 分钟粒度的一天）；
    - `days_window`：只使用最近多少天的数据建模，0 表示使用全部历史；
    - `degree`：趋势多项式阶数（1~3），控制趋势的复杂度；
    - `robust`：是否启用鲁棒分解，减弱异常点影响；
  - 点击“运行预测”后，由前端发起 HTTP 请求调用后端预测接口（待启用）。

- **后端脚本调用示例思路**（不涉及接口实现细节，仅说明流程）：
  1. 将待预测的时间序列 CSV 放入 `backend/uploads/` 目录；
  2. 在脚本中实例化 `PredictionService`；
  3. 调用 `sarima_timeseries_prediction(
       filename=..., area_column=..., order=(1,1,1), stl_reg_params={...}
     )` 获取预测结果；
  4. 使用返回的 `history_* / train_* / test_* / future_* / metrics` 字段，在 Notebook 或前端绘制训练/测试/未来三段曲线，评估预测效果。

这样，在后续重新打开 `/api/analysis/predict` 时，可以直接将上述参数通过 JSON 传入，前端复用同一套可视化逻辑展示预测结果。

---

## 部署与扩展建议（简要）

- **部署**
  - 后端：`uvicorn` 或 `gunicorn + uvicorn workers`，放在 Nginx 后面统一暴露 API。
  - 前端：`npm run build` 后将 `dist/` 静态文件交由 Nginx/静态服务器托管。
  - 前后端通过同一域名不同路径（如 `/` + `/api`）配置。

- **扩展**
  - 引入用户与权限体系（基于 FastAPI 认证中间件）。
  - 将异常检测/聚类/预测任务接入异步队列（如 Celery + Redis）。
  - 将当前单机内存 `TaskManager` 替换为可持久化的任务存储（Redis 等）。
  - 完善预测模块，对接多模型（XGBoost/LightGBM/CatBoost/LSTM 等）统一评估框架。

---
