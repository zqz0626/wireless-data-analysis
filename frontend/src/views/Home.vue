<script>
/**
 * 首页组件
 * 展示系统介绍、技术栈和功能模块目录
 * 包含翻页动画效果和最终欢迎页
 */
export default {
  name: 'Home',
  data() {
    return {
      // 右侧功能模块目录配置
      rightModules: [
        {
          key: 'data-manage',
          title: '数据管理',
          en: 'Data Management',
          desc: '提供多格式数据文件的上传、预览、导出与版本管理，为后续预处理和建模提供统一、可追溯的数据入口。'
        },
        {
          key: 'preprocess',
          title: '预处理配置',
          en: 'Preprocess',
          desc: '支持数据清洗、特征工程和多源数据对齐，配合质量评估构建适合建模的高质量特征数据。'
        },
        {
          key: 'anomaly-detection',
          title: '异常检测',
          en: 'Anomaly Detection',
          desc: '基于多维数值特征和孤立森林等无监督方法发现异常点，并通过分数、触发特征和时间轴可视化帮助理解异常模式，支持历史模型记录与复用。'
        },
        {
          key: 'clustering-analysis',
          title: '聚类分析',
          en: 'Clustering Analysis',
          desc: '集成多种聚类算法并提供可视化与簇特征画像，从维度对区域进行分群和趋势分类，支持历史模型记录与复用。'
        },
        {
          key: 'prediction',
          title: '预测分析',
          en: 'Prediction Analysis',
          desc: '支持统计、机器学习、混合与深度学习等多类预测算法，并通过误差指标与曲线对比可视化评估预测效果，支持历史模型记录与复用。'
        }
      ],
      // 技术栈相关配置
      techStackTitle: '技术栈',
      techStackEn: 'Tech Stack',
      techStackFrontend: 'Frontend: Vue 3 + Vue Router + Element Plus + Vite',
      techStackFrontendEn: '前端',
      techStackBackend: 'Backend: FastAPI + Uvicorn + Pydantic',
      techStackBackendEn: '后端',
      techStackDatabase: 'Database: MySQL + SQLAlchemy',
      techStackDatabaseEn: '数据库',
      // 左侧阶段：0=标题页，1=前端技术栈，2=后端技术栈，3=数据库技术栈，4=空白
      leftStage: 0,
      // 右侧阶段：0=目录页，1=数据管理，2=预处理，3=异常检测，4=聚类分析，5=预测分析，6=空白
      rightStage: 0,
      // 动画节流控制，防止快速点击
      isLeftAnimating: false,
      isRightAnimating: false,
      // 控制最终欢迎页是否显示
      showFinalWelcome: false
    }
  },
  computed: {
    /**
     * 获取左侧当前阶段类型
     * @returns {string} 阶段类型：intro|frontend|backend|database|none
     */
    leftStageType() {
      const map = ['intro', 'frontend', 'backend', 'database', 'none']
      return map[this.leftStage] || 'intro'
    },
    /**
     * 获取右侧当前阶段类型
     * @returns {string} 阶段类型：directory|data-manage|preprocess|anomaly|cluster|prediction|none
     */
    rightStageType() {
      const map = ['directory', 'data-manage', 'preprocess', 'anomaly', 'cluster', 'prediction', 'none']
      return map[this.rightStage] || 'directory'
    }
  },
  methods: {
    /**
     * 左侧翻页处理
     * 点击图钉后，当前页掉落，显示下一页
     */
    nextLeftStage() {
      if (this.isLeftAnimating || this.leftStage >= 4) return
      this.isLeftAnimating = true
      
      // 0.8秒后切换到下一页，确保动画流畅
      setTimeout(() => {
        this.leftStage += 1
        this.isLeftAnimating = false
        this.checkShowFinalWelcome()
      }, 800)
    },
    /**
     * 右侧翻页处理
     * 点击图钉后，当前页掉落，显示下一页
     */
    nextRightStage() {
      if (this.isRightAnimating || this.rightStage >= 6) return
      this.isRightAnimating = true
      
      // 0.8秒后切换到下一页，确保动画流畅
      setTimeout(() => {
        this.rightStage += 1
        this.isRightAnimating = false
        this.checkShowFinalWelcome()
      }, 800)
    },
    /**
     * 检查是否显示最终欢迎页
     * 当左右两侧都进入none阶段时，0.5秒后显示欢迎页
     */
    checkShowFinalWelcome() {
      if (!this.showFinalWelcome && this.leftStageType === 'none' && this.rightStageType === 'none') {
        setTimeout(() => {
          this.showFinalWelcome = true
        }, 500)
      }
    },
    /**
     * 从最终欢迎页返回首页初始状态
     */
    enterSystemFromWelcome() {
      this.leftStage = 0
      this.rightStage = 0
      this.showFinalWelcome = false
    },
    /**
     * 跳转到指定功能模块
     * @param {string} path - 模块路由路径
     */
    goToModule(path) {
      this.$router.push(path)
    },
    /**
     * 进入系统应用
     * 如果当前在初始状态，先显示最终欢迎页；否则直接跳转到数据管理页面
     */
    goToApp() {
      if (this.leftStage === 0 && this.rightStage === 0) {
        this.leftStage = 4
        this.rightStage = 6
        this.checkShowFinalWelcome()
        return
      }
      this.$router.push('/app/data-manage')
    }
  }
}
</script>

<template>
  <div class="home-root">
    <div class="home-hero">
      <!-- 左半屏：标题 / 前端栈 / 后端栈 -->
      <div
        v-if="!(leftStageType === 'none' && rightStageType === 'none')"
        class="home-hero-left"
        :class="{ 'home-hero-left-empty': leftStageType === 'none' }"
      >
        <!-- 顶部图钉：始终显示，控制左侧阶段前进 -->
        <div
          class="pin top-center"
          @click="nextLeftStage"
        ></div>

        <!-- 阶段 0：系统标题 -->
        <transition name="fall-down">
          <div v-if="leftStageType === 'intro'" class="home-hero-content">
            <h1 class="home-title-cn clickable" @click="goToApp">无线大数据分析系统</h1>
            <p class="home-title-en">wireless-data-analysis system</p>

            <!-- 技术栈概要 -->
            <div class="tech-stack-footer">
              <div class="tech-stack-row">
                <span class="tech-stack-title-cn">{{ techStackTitle }}</span>
                <span class="tech-stack-title-en">{{ techStackEn }}</span>
              </div>
              <div class="tech-stack-row">
                <span class="tech-stack-title-cn">{{ techStackFrontendEn }}</span>
                <span class="tech-stack-title-en">{{ techStackFrontend }}</span>
              </div>
              <div class="tech-stack-row">
                <span class="tech-stack-title-cn">{{ techStackBackendEn }}</span>
                <span class="tech-stack-title-en">{{ techStackBackend }}</span>
              </div>
              <div class="tech-stack-row">
                <span class="tech-stack-title-cn">{{ techStackDatabaseEn }}</span>
                <span class="tech-stack-title-en">{{ techStackDatabase }}</span>
              </div>
            </div>
          </div>
        </transition>

        <!-- 阶段 1：前端技术栈 -->
        <transition name="fall-down">
          <div v-if="leftStageType === 'frontend'" class="tech-stack-detail-content frontend-stack">
            <div class="tech-stack-header">前端技术栈</div>
            <div class="tech-stack-body">
              <div class="tech-section">
                <div class="tech-section-content">
                  <div class="tech-item">
                    <span class="tech-item-name">Vue 3</span>
                    <span class="tech-item-desc">作为单页应用核心框架，负责整体视图和组件化开发，是前端界面的基础支撑</span>
                  </div>
                  <div class="tech-item">
                    <span class="tech-item-name">Vue Router 4</span>
                    <span class="tech-item-desc">负责前端路由管理，实现多视图页面切换和导航控制</span>
                  </div>
                  <div class="tech-item">
                    <span class="tech-item-name">Element Plus</span>
                    <span class="tech-item-desc">基于 Vue 3 的 UI 组件库，用于快速搭建分析类界面和常见交互组件</span>
                  </div>
                  <div class="tech-item">
                    <span class="tech-item-name">Vite</span>
                    <span class="tech-item-desc">作为前端构建与开发工具，提供开发服务器与打包能力，简化前端工程化流程</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </transition>

        <!-- 阶段 2：后端技术栈 -->
        <transition name="fall-down">
          <div v-if="leftStageType === 'backend'" class="tech-stack-detail-content backend-stack">
            <div class="tech-stack-header backend-title">后端技术栈</div>
            <div class="tech-stack-body">
              <div class="tech-section">
                <div class="tech-section-content">
                  <div class="tech-item">
                    <span class="tech-item-name">FastAPI</span>
                    <span class="tech-item-desc">作为后端 Web 框架，构建 RESTful 风格接口服务，统一对外提供数据访问能力</span>
                  </div>
                  <div class="tech-item">
                    <span class="tech-item-name">Uvicorn</span>
                    <span class="tech-item-desc">作为 ASGI 服务器运行 FastAPI 应用，负责请求接入与服务运行</span>
                  </div>
                  <div class="tech-item">
                    <span class="tech-item-name">Pydantic</span>
                    <span class="tech-item-desc">在 FastAPI 中负责请求参数校验与数据模型定义，提升接口的数据规范性</span>
                  </div>
                  <div class="tech-item">
                    <span class="tech-item-name">pydantic-settings</span>
                    <span class="tech-item-desc">用于管理应用配置与环境变量，支持不同环境下的统一配置管理</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </transition>
        
        <!-- 阶段 3：数据库技术栈 -->
        <transition name="fall-down">
          <div v-if="leftStageType === 'database'" class="tech-stack-detail-content backend-stack">
            <div class="tech-stack-header backend-title">数据库技术栈</div>
            <div class="tech-stack-body">
              <div class="tech-section">
                <div class="tech-section-content">
                  <div class="tech-item">
                    <span class="tech-item-name">MySQL</span>
                    <span class="tech-item-desc">作为关系型数据库，存储系统配置、模板数据和分析结果，提供可靠的数据持久化支持</span>
                  </div>
                  <div class="tech-item">
                    <span class="tech-item-name">SQLAlchemy</span>
                    <span class="tech-item-desc">作为 Python ORM 框架，简化数据库操作，提供统一的数据访问接口，支持多种数据库后端</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </transition>
      </div>

      <!-- 右半屏：目录 / 数据处理模块 / 预测模块 -->
      <div
        v-if="!(leftStageType === 'none' && rightStageType === 'none')"
        class="home-hero-right"
        :class="{ 'home-hero-right-empty': rightStageType === 'none' }"
      >
        <!-- 顶部图钉：始终显示，控制右侧阶段前进 -->
        <div
          class="pin top-center"
          @click="nextRightStage"
        ></div>

        <!-- 阶段 0：目录页 -->
        <transition name="fall-down">
          <div v-if="rightStageType === 'directory'" class="book-content">
            <div class="book-header">目录</div>
            <div class="book-body">
              <div
                v-for="item in rightModules"
                :key="item.key"
                class="book-row"
              >
                <div class="book-row-main">
                  <span class="book-title-cn">{{ item.title }}</span>
                  <span class="book-title-en">{{ item.en }}</span>
                </div>
              </div>
            </div>
          </div>
        </transition>

        <!-- 阶段 1：数据管理 -->
        <transition name="fall-down">
          <div v-if="rightStageType === 'data-manage'" class="module-detail-content">

            <div class="module-header">数据管理</div>
            <div class="module-body">
              <div class="module-item">
                <span class="module-item-name">文件上传</span>
                <span class="module-item-desc">支持 CSV、JSON 格式的数据文件上传，并设置关联，统一接入原始业务数据。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">数据预览与基础分析</span>
                <span class="module-item-desc">通过表格与基础统计信息快速了解字段结构和数据分布情况，便于检查数据质量。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">数据导出</span>
                <span class="module-item-desc">将未处理，处理后的文件或地图文件导出。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">版本管理</span>
                <span class="module-item-desc">对上传与处理后的数据进行版本控制，支持历史版本回滚和对比，保障可追溯性。</span>
              </div>
            </div>
          </div>
        </transition>

        <!-- 阶段 2：预处理配置 -->
        <transition name="fall-down">
          <div v-if="rightStageType === 'preprocess'" class="module-detail-content">

            <div class="module-header">预处理配置</div>
            <div class="module-body">
              <div class="module-item">
                <span class="module-item-name">缺失值填补</span>
                <span class="module-item-desc">对缺失观测进行插值或填补处理，减少空值对统计分析和建模结果的干扰。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">数据标准化</span>
                <span class="module-item-desc">通过归一化或标准差标准化等方式对数值型字段进行缩放，消除量纲差异对模型训练的影响。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">质量评估</span>
                <span class="module-item-desc">对预处理后的数据进行完整性、一致性等质量检查，并给出简要提示，帮助发现明显问题。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">生成文件</span>
                <span class="module-item-desc">将预处理后的结果保存或导出为标准化数据文件，作为后续异常检测、聚类和预测分析的输入。</span>
              </div>
            </div>
          </div>
        </transition>

        <!-- 阶段 3：异常检测 -->
        <transition name="fall-down">
          <div v-if="rightStageType === 'anomaly'" class="module-detail-content">

            <div class="module-header">异常检测</div>
            <div class="module-body">
              <div class="module-item">
                <span class="module-item-name">异常检测算法</span>
                <span class="module-item-desc">基于 Isolation Forest 无监督算法，对多个地区的数据进行异常点挖掘。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">插值修正</span>
                <span class="module-item-desc">通过线性插值等方法对缺失或明显异常的观测点进行修正，减少噪声对后续异常分析的干扰。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">异常结果解释</span>
                <span class="module-item-desc">为每条异常样本提供异常分数、触发特征和严重等级（高/中/低）等解释信息。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">时间轴可视化</span>
                <span class="module-item-desc">以时间轴散点图形式展示正常点与异常点分布，并支持按指定指标高亮异常。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">生成文件</span>
                <span class="module-item-desc">将异常检测结果导出为标准化文件，便于后续审查、归档或与其他系统联动。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">历史模型记录</span>
                <span class="module-item-desc">支持保存和管理历史检测模型，可快速加载复用之前的配置和结果，提高分析效率。</span>
              </div>
            </div>
          </div>
        </transition>

        <!-- 阶段 4：聚类分析 -->
        <transition name="fall-down">
          <div v-if="rightStageType === 'cluster'" class="module-detail-content">

            <div class="module-header">聚类分析</div>
            <div class="module-body">
              <div class="module-item">
                <span class="module-item-name">聚类算法</span>
                <span class="module-item-desc">提供 K-Means、层次聚类、GMM 多种无监督算法，适应含噪声和不规则簇等不同数据形态。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">k 值估计和指标评估</span>
                <span class="module-item-desc">通过轮廓系数等聚类指标评估不同 k 值下的效果，辅助选择合适的簇数并分析聚类质量。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">聚类可视化</span>
                <span class="module-item-desc">可结合地图对各簇进行空间分布展示，并配合柱状图和饼图展现簇内指标结构和占比情况。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">各簇趋势显示</span>
                <span class="module-item-desc">结合时间序列行为展示各簇关键指标的走势，在同一数轴上绘制折线图对比更明显。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">历史模型记录</span>
                <span class="module-item-desc">支持保存和管理历史聚类模型，可快速加载复用之前的配置和结果，提高分析效率。</span>
              </div>
            </div>
          </div>
        </transition>

        <!-- 阶段 5：预测分析 -->
        <transition name="fall-down">
          <div v-if="rightStageType === 'prediction'" class="module-detail-content">
            <div class="module-header">预测分析</div>
            <div class="module-body">
              <div class="module-item">
                <span class="module-item-name">统计模型</span>
                <span class="module-item-desc">包含 STL + 线性回归和 SARIMA 等统计模型，用于对趋势和季节性较稳定的指标进行可解释的短期预测。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">机器学习模型</span>
                <span class="module-item-desc">提供 XGBoost、LightGBM、CatBoost 以及 XGBoost + 随机森林（残差）等模型，结合多种历史特征进行非线性回归预测。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">深度学习模型</span>
                <span class="module-item-desc">包含 LSTM、GRU、CNN、TCN 等深度时序网络，用于挖掘复杂非线性时间序列模式。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">大模型</span>
                <span class="module-item-desc">通过本地大模型预测（qwen2.5:7b）配合 Ollama，对复杂场景的时间序列进行生成式预测与分析。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">预测结果可视化与分析</span>
                <span class="module-item-desc">通过折线图和误差指标对比展示不同算法在多区域的预测效果，用于选择最优方案和评估模型质量。</span>
              </div>
              <div class="module-item">
                <span class="module-item-name">历史模型记录</span>
                <span class="module-item-desc">支持保存和管理历史预测模型，可快速加载复用之前的配置和结果，提高分析效率。</span>
              </div>
            </div>
          </div>
        </transition>
      </div>

      <div
        v-if="showFinalWelcome"
        class="welcome-overlay"
      >
        <div class="welcome-tags">
          <div class="welcome-tag tag-data" @click.stop="goToModule('/app/data-manage')">
            <div class="welcome-tag-cn">数据管理</div>
            <div class="welcome-tag-en">Data Management</div>
          </div>
          <div class="welcome-tag tag-preprocess" @click.stop="goToModule('/app/preprocess')">
            <div class="welcome-tag-cn">预处理配置</div>
            <div class="welcome-tag-en">Preprocess</div>
          </div>
          <div class="welcome-tag tag-anomaly" @click.stop="goToModule('/app/anomaly')">
            <div class="welcome-tag-cn">异常检测</div>
            <div class="welcome-tag-en">Anomaly Detection</div>
          </div>
          <div class="welcome-tag tag-cluster" @click.stop="goToModule('/app/cluster')">
            <div class="welcome-tag-cn">聚类分析</div>
            <div class="welcome-tag-en">Clustering Analysis</div>
          </div>
          <div class="welcome-tag tag-predict" @click.stop="goToModule('/app/predict')">
            <div class="welcome-tag-cn">预测分析</div>
            <div class="welcome-tag-en">Prediction Analysis</div>
          </div>
        </div>
        <div class="welcome-card" @click.stop="enterSystemFromWelcome">
          <div class="welcome-title-cn">欢迎使用无线大数据分析系统</div>
          <div class="welcome-title-en">Welcome to the wireless-data-analysis system</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 首页组件样式 */

/* 英雄区内容样式 */
.home-hero-content {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  text-align: center;
  padding: 40px 32px;
  position: absolute;
  width: 100%;
}

/* 技术栈页脚样式 */
.tech-stack-footer {
  margin-top: 60px;
  padding-top: 20px;
  border-top: 1px solid rgba(183, 110, 121, 0.4);
  text-align: center;
  width: 100%;
}

.tech-stack-row {
  margin-bottom: 6px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
}

.tech-stack-row:last-child {
  margin-bottom: 0;
}

.tech-stack-title-cn {
  font-weight: 400;
  font-family: 'Georgia', 'Times New Roman', serif;
  font-style: italic;
  color: #8b7a6f;
  font-size: 0.85rem;
  opacity: 0.7;
}

.tech-stack-title-en {
  font-family: 'Brush Script MT', 'Segoe Script', cursive;
  font-style: italic;
  color: #8b7a6f;
  font-size: 0.8rem;
  opacity: 0.6;
}

/* 图钉样式 */
.pin {
  position: absolute;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, #e8c4a0, #b76e79 40%, #8b5a5f);
  box-shadow: 
    0 2px 6px rgba(0, 0, 0, 0.4),
    inset 0 -2px 4px rgba(0, 0, 0, 0.3),
    inset 2px 2px 4px rgba(255, 255, 255, 0.4);
  z-index: 10;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pin:hover {
  transform: scale(1.1) translateX(-50%);
  box-shadow: 
    0 4px 8px rgba(0, 0, 0, 0.5),
    inset 0 -2px 4px rgba(0, 0, 0, 0.3),
    inset 2px 2px 4px rgba(255, 255, 255, 0.4);
}

.pin::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
}

/* 图钉刺入效果 */
.pin::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  width: 8px;
  height: 16px;
  background: linear-gradient(to bottom, #8b5a5f, #6b4a4f);
  border-radius: 0 0 4px 4px;
  z-index: -1;
}

/* 图钉位置 - 顶部居中 */
.pin.top-center {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
}

/* 英文标题样式 */
.home-title-en {
  margin-bottom: 16px;
  font-size: 1.1rem;
  font-weight: 500;
  font-family: 'Brush Script MT', 'Segoe Script', cursive;
  font-style: italic;
  color: #4a3a2e;
  opacity: 0.8;
}

/* 可点击标题样式 */
.home-title-cn.clickable {
  cursor: pointer;
  transition: all 0.3s ease;
}

.home-title-cn.clickable:hover {
  transform: scale(1.02);
  filter: brightness(1.1) drop-shadow(0 4px 8px rgba(183, 110, 121, 0.5));
}

/* 目录页样式 */
.book-content {
  width: 100%;
  height: 100%;
  padding: 40px 32px;
  display: flex;
  flex-direction: column;
  position: absolute;
  align-items: center;
}

.book-header {
  font-size: 2.5rem;
  font-weight: 800;
  margin-bottom: 32px;
  text-align: center;
  font-family: 'Georgia', 'Times New Roman', serif;
  font-style: italic;
  letter-spacing: 0.08em;
  color: #c17c7e;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.15);
  line-height: 1.2;
}

.book-body {
  display: flex;
  flex-direction: column;
  height: calc(100% - 80px);
  gap: 20px;
  width: 100%;
  max-width: 700px;
  margin: 0 auto;
  overflow-y: hidden;
  padding-right: 0;
  justify-content: space-around;
}

/* 隐藏滚动条但保留滚动功能 */
.book-body {
  -ms-overflow-style: none;  /* IE and Edge */
  scrollbar-width: none;  /* Firefox */
}

/* 隐藏WebKit浏览器滚动条 */
.book-body::-webkit-scrollbar {
  display: none;
}

/* 透明卡片样式 - 文字直接写在书页上效果 */
.book-row {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 25px 24px;
  margin: 0;
  background: transparent;
  border-radius: 16px;
  border: 1px solid transparent;
  box-shadow: none;
  transition: all 0.3s ease;
  min-height: 100px;
  height: auto;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  text-align: center;
  width: 100%;
  max-width: 650px;
  margin: 0 auto;
}

/* 移除卡片装饰元素 */
.book-row::before {
  display: none;
}

/* 卡片悬停效果 - 透明背景下的简洁效果 */
.book-row:hover {
  border-color: rgba(183, 110, 121, 0.4);
  background: rgba(250, 248, 240, 0.3);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); /* 非常淡的阴影效果 */
}

/* 卡片内容布局 - 标题居左，英文居右 */
.book-row-main {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0;
  gap: 16px;
  position: relative;
  z-index: 1;
  width: 100%;
  flex-wrap: nowrap;
}

/* 中文标题样式 - 居左 */
.book-title-cn {
  font-weight: 800;
  font-size: 1.3rem;
  font-family: 'Georgia', 'Times New Roman', serif;
  font-style: italic;
  letter-spacing: 0.03em;
  color: #3a2f24;
  line-height: 1.3;
  margin: 0;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  position: relative;
  white-space: nowrap;
  text-align: left;
  flex-shrink: 0;
}

/* 中文标题悬停效果 - 简化，只保留颜色变化 */
.book-row:hover .book-title-cn {
  color: #b76e79;
  text-shadow: 1px 1px 3px rgba(183, 110, 121, 0.2);
}

/* 英文标题样式 - 居右 */
.book-title-en {
  font-size: 0.9rem;
  opacity: 0.8;
  font-family: 'Brush Script MT', 'Segoe Script', cursive;
  font-style: italic;
  color: #6a5a4e;
  margin: 0;
  text-transform: none;
  letter-spacing: 0.1em;
  transition: all 0.3s ease;
  position: relative;
  white-space: nowrap;
  text-align: right;
  flex-shrink: 0;
}

/* 英文标题悬停效果 - 简化，只保留颜色变化 */
.book-row:hover .book-title-en {
  color: #c17c7e;
  opacity: 1;
  font-size: 0.95rem;
}

/* 移除发光效果 */

/* 书页翻转动画 */
.fall-down-enter-active {
  transition: all 0.5s ease;
  position: absolute;
  width: 100%;
  height: 100%;
}

.fall-down-leave-active {
  transition: all 0.8s ease;
  position: absolute;
  width: 100%;
  height: 100%;
}

/* 进入动画：淡入浮现 */
.fall-down-enter-from {
  opacity: 0;
  transform: translateY(0);
}

.fall-down-enter-to {
  opacity: 1;
  transform: translateY(0);
}

/* 离开动画：向下掉落并旋转 */
.fall-down-leave-from {
  opacity: 1;
  transform: translateY(0) rotateZ(0deg);
}

.fall-down-leave-to {
  opacity: 0;
  transform: translateY(300px) rotateZ(15deg);
}

/* 技术栈详细页面样式 */
.tech-stack-detail-content {
  position: absolute;
  width: 100%;
  height: 100%;
  padding: 40px 32px;
  display: flex;
  flex-direction: column;
  text-align: center;
  overflow: hidden;
  align-items: center;
}

/* 阶段为空时的样式 */
.home-hero-left-empty {
  background: transparent !important;
  box-shadow: none !important;
}

.home-hero-right-empty {
  background: transparent !important;
  box-shadow: none !important;
}

/* 最终欢迎页样式 */
.welcome-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
  cursor: pointer;
}

.welcome-tags {
  position: absolute;
  inset: 0;
  pointer-events: auto;
}

.welcome-tag {
  position: absolute;
  padding: 20px 30px;
  border-radius: 4px;
  background: #fff8dc;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.25);
  font-size: 1rem;
  color: #554030;
  text-align: center;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.welcome-tag::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -6px;
  height: 8px;
  background-image: linear-gradient(90deg, rgba(0, 0, 0, 0.08) 0, transparent 10%, rgba(0, 0, 0, 0.08) 25%, transparent 40%, rgba(0, 0, 0, 0.08) 55%, transparent 70%, rgba(0, 0, 0, 0.08) 85%, transparent 100%);
  opacity: 0.6;
}

.welcome-tag-cn {
  font-size: 1.8rem;
  font-weight: 800;
  font-family: 'Georgia', 'Times New Roman', serif;
  font-style: italic;
  color: #c17c7e;
}

.welcome-tag-en {
  font-size: 0.95rem;
  opacity: 0.8;
  margin-top: 4px;
  font-family: 'Brush Script MT', 'Segoe Script', cursive;
}

/* 各功能模块标签位置和样式 */
.welcome-tag.tag-data {
  top: 18%;
  left: 14%;
  transform: scale(1.5) rotate(-6deg);
}

.welcome-tag.tag-data:hover {
  transform: scale(1.62) translateY(-3px) rotate(-6deg);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.3);
}

.welcome-tag.tag-preprocess {
  top: 18%;
  right: 10%;
  transform: scale(1.5) rotate(4deg);
}

.welcome-tag.tag-preprocess:hover {
  transform: scale(1.62) translateY(-3px) rotate(4deg);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.3);
}

.welcome-tag.tag-anomaly {
  bottom: 22%;
  left: 8%;
  transform: scale(1.5) rotate(2deg);
}

.welcome-tag.tag-anomaly:hover {
  transform: scale(1.62) translateY(-3px) rotate(2deg);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.3);
}

.welcome-tag.tag-cluster {
  bottom: 30%;
  right: 6%;
  transform: scale(1.5) rotate(-4deg);
}

.welcome-tag.tag-cluster:hover {
  transform: scale(1.62) translateY(-3px) rotate(-4deg);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.3);
}

.welcome-tag.tag-predict {
  bottom: 12%;
  right: 36%;
  transform: scale(1.5) rotate(-2deg);
}

.welcome-tag.tag-predict:hover {
  transform: scale(1.62) translateY(-3px) rotate(-2deg);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.3);
}

/* 中央欢迎卡片 */
.welcome-card {
  padding: 40px 56px;
  border-radius: 10px;
  background: #fff8dc;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.22), 0 0 0 1px rgba(183, 110, 121, 0.18);
  text-align: center;
  transform: translateY(0);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  position: relative;
}

.welcome-title-cn {
  font-size: 2.8rem;
  font-weight: 800;
  margin-bottom: 12px;
  font-family: 'Georgia', 'Times New Roman', serif;
  font-style: italic;
  letter-spacing: 0.04em;
  color: #c17c7e;
}

.welcome-title-en {
  font-size: 1.2rem;
  opacity: 0.8;
  margin-bottom: 16px;
  font-family: 'Brush Script MT', 'Segoe Script', cursive;
}

.welcome-card:hover {
  transform: scale(1.08) translateY(-3px);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.3);
}

.welcome-card::after {
  content: '';
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: -8px;
  height: 10px;
  background-image: linear-gradient(90deg, rgba(0, 0, 0, 0.1) 0, transparent 12%, rgba(0, 0, 0, 0.1) 28%, transparent 45%, rgba(0, 0, 0, 0.1) 62%, transparent 78%, rgba(0, 0, 0, 0.1) 94%, transparent 100%);
  opacity: 0.75;
}

/* 技术栈标题样式 */
.tech-stack-header {
  font-size: 1.8rem;
  font-weight: 800;
  margin-bottom: 32px;
  font-family: 'Georgia', 'Times New Roman', serif;
  font-style: italic;
  letter-spacing: 0.05em;
  color: #c17c7e;
}

.tech-stack-header.backend-title {
  font-size: 1.8rem;
  margin-bottom: 32px;
}

/* 技术栈内容样式 */
.tech-stack-body {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  text-align: left;
  flex: 1;
  justify-content: space-around;
  height: 100%;
  padding-right: 0;
}

.tech-section {
  width: 100%;
  height: 100%;
}

.tech-section-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  text-align: left;
  flex: 1;
  justify-content: space-around;
  height: 100%;
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
  padding-right: 0;
}

/* 统一透明标签样式 */
.tech-item,
.module-item {
  padding: 16px 20px;
  background: transparent;
  border-radius: 10px;
  border-left: 4px solid #b76e79;
  border-right: 1px solid transparent;
  border-bottom: 1px solid transparent;
  box-shadow: none;
  transition: all 0.3s ease;
  min-height: 70px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  width: 100%;
  flex-shrink: 0;
}

/* 统一标签名称样式 */
.tech-item-name,
.module-item-name {
  font-size: 1.05rem;
  font-weight: 700;
  font-family: 'Georgia', 'Times New Roman', serif;
  font-style: italic;
  color: #3a2f24;
  margin-bottom: 6px;
  width: 100%;
  line-height: 1.2;
  flex-shrink: 0;
}

/* 统一标签描述样式 */
.tech-item-desc,
.module-item-desc {
  font-size: 0.85rem;
  color: #5a4a3e;
  opacity: 0.88;
  max-width: 100%;
  text-align: left;
  width: 100%;
  line-height: 1.5;
  margin-left: 0;
  margin-top: 0;
  flex-shrink: 0;
  display: -webkit-box;
  display: -moz-box;
  display: box;
  -webkit-line-clamp: 2;
  -moz-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  -moz-box-orient: vertical;
  box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 前端/后端技术栈标签样式 */
.frontend-stack .tech-section-content,
.backend-stack .tech-section-content {
  gap: 12px;
  flex: 1;
  justify-content: space-around;
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
  padding-right: 0;
}

/* 模块详情页面样式 */
.module-detail-content {
  position: absolute;
  width: 100%;
  height: 100%;
  padding: 40px 32px;
  display: flex;
  flex-direction: column;
  text-align: center;
  overflow: hidden;
  align-items: center;
}

.module-body {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  text-align: left;
  flex: 1;
  justify-content: space-around;
  height: 100%;
  padding-right: 0;
}

.module-header {
  font-size: 1.8rem;
  font-weight: 800;
  margin-bottom: 32px;
  font-family: 'Georgia', 'Times New Roman', serif;
  font-style: italic;
  letter-spacing: 0.05em;
  color: #c17c7e;
  text-align: center;
  flex-shrink: 0;
}

/* 悬停效果 */
.tech-item:hover,
.module-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  background: linear-gradient(135deg, rgba(250, 248, 240, 0.9), rgba(245, 230, 210, 0.7));
  border-left: 4px solid #c17c7e;
  transition: all 0.3s ease;
}
</style>