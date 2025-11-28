<template>
  <div class="app-root">
    <!-- global banner removed per design: keep header minimal -->
    <div class="app-layout">
    <!-- 侧边栏导航 -->
  <aside class="sidebar" :class="{ collapsed: !isSidebarOpen }">
      <!-- sidebar header removed to declutter left-top branding -->
      <nav class="sidebar-nav">
        <router-link
          :to="{ name: 'DataManage' }"
          class="nav-item"
          :class="{ active: route.name === 'DataManage' }"
        >
          <el-icon><Document /></el-icon>
          <span>数据管理</span>
        </router-link>
        <router-link
          :to="{ name: 'Preprocess' }"
          class="nav-item"
          :class="{ active: route.name === 'Preprocess' }"
        >
          <el-icon><Filter /></el-icon>
          <span>预处理配置</span>
        </router-link>
        <router-link
          :to="{ name: 'Anomaly' }"
          class="nav-item"
          :class="{ active: route.name === 'Anomaly' }"
        >
          <el-icon><Warning /></el-icon>
          <span>异常检测</span>
        </router-link>
        <router-link
          :to="{ name: 'Cluster' }"
          class="nav-item"
          :class="{ active: route.name === 'Cluster' }"
        >
          <el-icon><PieChart /></el-icon>
          <span>聚类分析</span>
        </router-link>
        <router-link
          :to="{ name: 'Predict' }"
          class="nav-item"
          :class="{ active: route.name === 'Predict' }"
        >
          <el-icon><DataAnalysis /></el-icon>
          <span>预测分析</span>
        </router-link>
      </nav>
    </aside>
    
    <!-- 主内容区域 -->
    <main class="main-content">
      <!-- 顶部导航栏 -->
      <header class="main-header">
        <div class="header-left">
          <button class="menu-toggle" @click="toggleSidebar" aria-label="切换侧栏">
            <el-icon><Menu /></el-icon>
          </button>
          <!-- 页面标题：从路由 meta.title 读取，显示在侧栏图标右侧 -->
          <div class="header-title" v-if="route && route.meta && route.meta.title">
            {{ route.meta.title }}
          </div>
        </div>
        <div class="header-right">
          <ThemeSelector />

          <router-link to="/" class="header-btn">
            <el-icon><Back /></el-icon>
            <span v-if="isSidebarOpen">退出应用</span>
          </router-link>
        </div>
      </header>

      <!-- 页面内容：对子路由使用 keep-alive 缓存，侧边栏切换时不销毁页面状态 -->
      <div class="page-container">
        <div class="page-content-inner">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <keep-alive>
                <component :is="Component" />
              </keep-alive>
            </transition>
          </router-view>
        </div>
      </div>
    </main>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElIcon } from 'element-plus'
import ThemeSelector from './ThemeSelector.vue'
import {
  Document,
  Filter,
  Warning,
  PieChart,
  DataAnalysis,
  Menu,
  Back
} from '@element-plus/icons-vue'

export default {
  name: 'AppLayout',
  components: {
    ElIcon,
    Document,
    Filter,
    Warning,
    PieChart,
    DataAnalysis,
    Menu,
    Back,
    ThemeSelector
  },
  setup() {
    const isSidebarOpen = ref(true)
    const route = useRoute()
    
    const toggleSidebar = () => {
      isSidebarOpen.value = !isSidebarOpen.value
    }
    
    // 初始化：读取持久化主题选择
    onMounted(() => {
      const root = document.documentElement
      const sel = localStorage.getItem('selectedTheme')
      const themes = ['theme-warm','theme-spring','theme-summer','theme-autumn','theme-winter','theme-aurora']
      themes.forEach(t => root.classList.remove(t))
      if (sel && themes.includes(sel)) {
        root.classList.add(sel)
      }
      // 兼容旧的 themeWarm 标记
      const warm = localStorage.getItem('themeWarm')
      if (warm === 'true' && !root.classList.contains('theme-warm')) {
        root.classList.add('theme-warm')
      }
    })

    return {
      isSidebarOpen,
      route,
      toggleSidebar
    }
  }
}
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  background-color: var(--background-color);
}

/* 侧边栏样式 */
  .sidebar {
  width: 200px;
  background-color: var(--sidebar-bg);
  color: var(--sidebar-text);
  transition: width 0.3s ease;
  box-shadow: 2px 0 6px rgba(0, 0, 0, 0.1);
  z-index: 100;
}

/* sidebar header intentionally removed */

.sidebar-nav {
  padding: 1rem 0;
}

.nav-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 0.75rem 1rem;
  color: var(--sidebar-text);
  text-decoration: none;
  transition: all 0.18s ease;
  cursor: pointer;
  width: 100%;
  box-sizing: border-box;
  gap: 12px;
}

.nav-item:hover {
  background-color: rgba(6,40,34,0.06);
  color: var(--sidebar-text);
  border-radius: var(--radius-lg);
}
.nav-item.active {
  background-color: rgba(6,40,34,0.12);
  color: var(--sidebar-text);
  border-radius: var(--radius-lg);
}
.nav-item el-icon {
  margin: 0;
  font-size: 1.1rem; /* 稍微增大图标以平衡行布局 */
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--sidebar-text);
}

.nav-item span {
  display: block;
  font-size: 0.98rem;
  line-height: 1;
  white-space: nowrap; /* 防止中文在收缩时逐字换行 */
  overflow: hidden;    /* 在过渡期间裁剪文字避免溢出 */
  max-width: 160px;    /* 与侧栏宽度匹配的最大宽度 */
  transition: opacity 0.18s ease, max-width 0.18s ease; /* 文字渐隐而非竖排过渡 */
}

/* 折叠样式：先隐藏文字，再收缩宽度，避免出现中间竖排效果 */
.sidebar.collapsed {
  width: 64px; /* 仅显示图标的紧凑宽度 */
}

.sidebar.collapsed .nav-item span {
  opacity: 0;
  max-width: 0; /* 立即将文字占位缩为0，避免折叠过程中的换行 */
}

/* 主内容区域 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.main-header {
  height: 60px;
  background-color: var(--surface-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  z-index: 50;
  /* 让主区头部左上角圆润，避免与深色侧栏形成方角 */
  border-top-left-radius: var(--radius-lg);
}

.menu-toggle {
  background: none;
  border: none;
  color: #333;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: var(--radius);
  transition: background-color 0.3s;
}

  .menu-toggle:hover {
  background-color: #f3f4f6;
}

.header-btn {
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
  color: var(--primary-color, #0f3a47);
  text-decoration: none;
  border-radius: 999px;
  background-color: #ffffff;
  border: 1px solid var(--primary-color, #7bc9ff);
  box-shadow: 0 2px 6px rgba(15,118,178,0.18);
  transition: all 0.25s ease;
}

.header-btn:hover {
  background-color: var(--primary-bg-hover, #e6f7ff);
  border-color: var(--primary-color-hover, #38bdf8);
}

.header-btn el-icon {
  margin-right: 6px;
}

/* Header title next to sidebar icon */
.header-title {
  margin-left: 12px;
  font-size: 1.375rem; /* increase slightly for readability */
  font-weight: 700;
  color: var(--primary-color);
  line-height: 1;
  display: inline-flex;
  align-items: center;
  white-space: nowrap; /* keep on one line */
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 520px; /* avoid overflowing header */
}

/* 隐藏页面内部的原始标题，避免与 header-title 重复显示 */
:deep(.page-content-inner h1),
:deep(.page-content-inner h2) {
  display: none !important;
}

/* Ensure header-left aligns icon and title on a single row */
.header-left {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

  .page-container {
  flex: 1;
  padding: 3rem 4rem 0; /* 顶部与左右保留间距，下方去除以实现底部齐平 */
  overflow-y: auto;
  display: flex;
  justify-content: center; /* 将内部内容居中 */
  /* 主容器也保留左上圆角并隐藏溢出，防止白色头部角落方正 */
  border-top-left-radius: var(--radius-lg);
  overflow: hidden;
  position: relative; /* 确保伪元素绝对定位基准 */
  /* 让主区背景与卡片面色一致，视觉更统一 */
  background: var(--surface-color);
}

/* 主内容内部容器：限制最大宽度并让卡片占据宽度 */
.page-content-inner {
  width: 100%;
  max-width: 1200px; /* 放大主区最大宽度，接近示例风格 */
  padding-bottom: var(--card-gap); /* 确保内部卡片有合适的下边距而不产生外层空白 */
}

/* 使主内容区与深色侧边栏背景更加贴合 */
.page-container::before {
  /* Disabled gradient overlay to avoid visible color banding. */
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  pointer-events: none;
  background: none !important;
}

/* 让页面内部卡片风格更柔和，和深色背景融合 */
:deep(.page-content-inner .el-card) {
  background: rgba(255,255,255,0.02) !important;
  border: 1px solid rgba(255,255,255,0.04) !important;
  box-shadow: 0 6px 18px rgba(3,7,18,0.35) !important;
  color: var(--text-primary) !important;
  border-radius: var(--radius-lg) !important;
}

/* 表格和描述性容器里的白色背景降低对比 */
:deep(.page-content-inner .el-descriptions),
:deep(.page-content-inner .el-table) {
  background: transparent !important;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    width: 200px;
  }
  
  .page-container {
    padding: 1rem;
  }
}
</style>