/**
 * 路由配置文件
 * 负责定义应用的路由结构、路由懒加载和路由守卫
 */

import { createRouter, createWebHistory } from 'vue-router'

/**
 * 路由懒加载配置
 * 使用动态导入() => import()实现路由组件的按需加载
 * 优点：
 * - 减少初始加载时间
 * - 提高应用性能
 * - 按需加载组件，只在访问时加载
 */
const Home = () => import('../views/Home.vue')           // 首页组件
const AppLayout = () => import('../components/AppLayout.vue') // 应用主布局组件
const DataManage = () => import('../views/DataManage.vue') // 数据管理组件
const Preprocess = () => import('../views/Preprocess.vue') // 数据预处理组件
const Anomaly = () => import('../views/Anomaly.vue')     // 异常检测组件
const Cluster = () => import('../views/Cluster.vue')     // 聚类分析组件
const Predict = () => import('../views/Predict.vue')     // 预测分析组件

/**
 * 路由配置数组
 * 定义应用的所有路由规则
 * 路由结构：
 * - 顶层路由：首页
 * - 应用布局路由组：包含所有功能页面
 * - 404路由：处理未匹配的路径
 */
const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home,
    meta: {
      title: '首页',          // 页面标题
      fullscreen: true        // 是否全屏显示（不显示头部）
    }
  },
  // 应用主布局路由组
  {
    path: '/app',
    component: AppLayout,     // 使用 AppLayout 作为父组件
    redirect: '/app/data-manage', // 默认重定向到数据管理页面
    children: [
      {
        path: 'data-manage',
        name: 'DataManage',
        component: DataManage,
        meta: {
          title: '数据管理'    // 页面标题：数据管理
        }
      },
      {
        path: 'preprocess',
        name: 'Preprocess',
        component: Preprocess,
        meta: {
          title: '预处理配置'  // 页面标题：预处理配置
        }
      },
      {
        path: 'anomaly',
        name: 'Anomaly',
        component: Anomaly,
        meta: {
          title: '异常检测'    // 页面标题：异常检测
        }
      },
      {
        path: 'cluster',
        name: 'Cluster',
        component: Cluster,
        meta: {
          title: '聚类分析'    // 页面标题：聚类分析
        }
      },
      {
        path: 'predict',
        name: 'Predict',
        component: Predict,
        meta: {
          title: '预测分析'    // 页面标题：预测分析
        }
      },
    ]
  },
  // 404页面：处理所有未匹配的路由
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'            // 重定向到首页
  }
]

/**
 * 创建路由实例
 * @param {Object} options - 路由配置选项
 * @param {string} options.history - 路由模式（createWebHistory：HTML5 History 模式）
 * @param {Array} options.routes - 路由配置数组
 */
const router = createRouter({
  history: createWebHistory(), // 使用 HTML5 History 模式
  routes                       // 路由配置
})

/**
 * 全局前置守卫
 * 在路由跳转前执行
 * 用途：
 * - 设置页面标题
 * - 权限验证
 * - 路由拦截
 */
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - 数据分析系统` : '数据分析系统'
  next() // 继续路由跳转
})

/**
 * 全局后置守卫
 * 在路由跳转完成后执行
 * 用途：
 * - 页面加载完成后的处理
 * - 统计分析
 * - 页面埋点
 */
router.afterEach(() => {
  // 可以在这里添加页面加载完成后的处理逻辑
  // 例如：滚动到顶部、页面加载动画结束等
})

// 导出路由实例
export default router