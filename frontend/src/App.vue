<script>
/**
 * 应用根组件
 * 负责管理应用的整体布局、头部显示逻辑和路由切换
 */
export default {
  name: 'App',
  /**
   * 生命周期钩子：组件挂载后
   * 功能：
   * - 添加滚动事件监听，实现导航栏滚动效果
   * - 初始化页面全屏状态
   */
  mounted() {
    // 添加滚动事件监听，实现导航栏滚动效果
    window.addEventListener('scroll', this.handleScroll);
    // 初始化页面全屏状态
    this.updateBodyFullscreenClass();
  },
  /**
   * 生命周期钩子：组件卸载前
   * 功能：
   * - 移除滚动事件监听，避免内存泄漏
   * - 清理 body 上的全屏类名
   */
  beforeUnmount() {
    // 移除滚动事件监听
    window.removeEventListener('scroll', this.handleScroll);
    // 清理 body 上的全屏类名
    const body = document.body
    if (body && body.classList) {
      body.classList.remove('fullscreen-page')
    }
  },
  /**
   * 组件方法
   */
  methods: {
    /**
     * 处理滚动事件
     * 功能：根据滚动距离为导航栏添加或移除 scrolled 类，实现滚动效果
     */
    handleScroll() {
      const header = document.querySelector('.app-header');
      if (!header) return;

      // 当滚动距离超过 10px 时，添加 scrolled 类
      if (window.scrollY > 10) {
        header.classList.add('scrolled');
      } else {
        header.classList.remove('scrolled');
      }
    },

    /**
     * 更新 body 的全屏类名
     * 功能：根据当前路由的 meta.fullscreen 属性或路由名称，决定是否为 body 添加 fullscreen-page 类
     */
    updateBodyFullscreenClass() {
      const body = document.body
      if (!body || !body.classList) return

      const route = this.$route
      // 判断是否需要全屏显示
      const fullscreen = (route?.meta && route.meta.fullscreen) || route?.name === 'Dashboard' || route?.name === 'Home'
      if (fullscreen) {
        body.classList.add('fullscreen-page')
      } else {
        body.classList.remove('fullscreen-page')
      }
    }
  },
  /**
   * 监听路由变化
   * 功能：当路由变化时，更新页面的全屏状态
   */
  watch: {
    $route() {
      this.updateBodyFullscreenClass()
    }
  }
}
</script>

<template>
  <div class="app-container">
    <header
      class="app-header"
      v-if="(!$route.meta || !$route.meta.fullscreen) && $route.name !== 'Home' && $route.path !== '/'"
    >
      <div class="header-content">
        <div class="brand-center">
          <h1>无线大数据分析系统</h1>
        </div>
      </div>
    </header>

    <!-- 普通页面：带内边距布局，由各自页面或布局组件决定是否显示头部 -->
    <main
      v-if="!$route.meta || !$route.meta.fullscreen"
      class="main-content"
    >
      <!-- 路由视图出口：使用 keep-alive 保持页面状态，在路由切换时不销毁组件 -->
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </transition>
      </router-view>
    </main>

    <!-- 全屏页面：交给子组件自己控制布局 -->
    <main
      v-else
      class="main-fullscreen"
    >
      <router-view v-slot="{ Component }">
        <component :is="Component" />
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: transparent;
  color: var(--text-primary);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: center;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
  padding: 0 var(--spacing-xl);
}

.app-header {
  background-color: var(--surface-color);
  color: var(--text-primary);
  padding: var(--spacing-md) 0;
  /* 不使用阴影隔开，改为明显的底部边线 */
  box-shadow: none !important;
  border-bottom: 2px solid rgba(11,43,36,0.10);
  position: sticky;
  top: 0;
  z-index: 100;
  transition: all var(--transition);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.app-header.scrolled {
  box-shadow: none !important;
  border-bottom: 2px solid rgba(11,43,36,0.12); /* 滚动时线条略微强化 */
}

.app-header h1 {
  font-size: 2rem;
  margin: 0;
  font-weight: 700;
  background: linear-gradient(to right, var(--primary-color), var(--accent-color));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 0.08em;
  text-shadow: 0 2px 6px rgba(0,0,0,0.08);
}

.brand-center {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.main-content {
  flex: 1;
  padding: var(--spacing-2xl) var(--spacing-xl);
  max-width: none;
  width: 100%;
  margin: 0;
}

.main-fullscreen {
  padding: 0;
}

/* 动画效果 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-slow) ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 响应式导航 */
@media (max-width: 768px) {
  .main-content {
    padding: var(--spacing-lg) var(--spacing-md);
  }
}
</style>