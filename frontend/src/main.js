/**
 * 应用入口文件
 * 负责初始化 Vue 应用、配置插件、加载样式和挂载应用
 */

import { createApp } from 'vue'

// 样式导入：按优先级从高到低排列
// 1. Element Plus 组件库样式
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

// 2. Vxe Table 组件库样式
import VXETable from 'vxe-table'
import 'vxe-table/lib/style.css'
import 'vxe-pc-ui/lib/style.css'

// 2. 项目全局样式
import './styles/index.css'    // 原有样式兼容性处理
import './styles/home.css'     // 首页相关样式（含滚动条控制）

// 3. 应用核心组件和路由
import App from './App.vue'     // 根组件
import router from './router'   // 路由配置

/**
 * 日志处理：定向屏蔽 ECharts 特定警告日志
 * 问题：ECharts 在某些配置下会重复输出 "cartesian2d cannot be found for series.line" 警告
 * 解决方案：拦截 console.error，过滤掉该特定警告，保留其他错误信息
 */
const __rawConsoleError = console.error.bind(console)
console.error = (...args) => {
  const msg = args[0]
  // 过滤掉特定的 ECharts 警告
  if (typeof msg === 'string' && msg.startsWith('[ECharts] cartesian2d cannot be found for series.line')) {
    return
  }
  // 其他错误正常输出
  __rawConsoleError(...args)
}

/**
 * 创建并配置 Vue 应用实例
 */
const app = createApp(App)

// 注册插件
app.use(router)      // 注册路由插件
app.use(ElementPlus) // 注册 Element Plus 组件库
app.use(VXETable)    // 注册 Vxe Table 组件库

/**
 * 应用初始化：恢复用户偏好设置
 * 在应用挂载前从 localStorage 中读取用户的主题偏好
 */
try {
  // 读取主题偏好（暖色主题）
  const themeWarm = localStorage.getItem('themeWarm')
  if (themeWarm === 'true') {
    document.documentElement.classList.add('theme-warm')
  }
  // 注意：sidebarVariant 模块已移除，相关持久化不再读取
} catch (e) {
  console.warn('无法读取本地存储偏好：', e)
}

/**
 * 挂载应用
 * 将应用实例挂载到 DOM 中的 #app 元素
 */
app.mount('#app')