/**
 * API 接口定义文件
 * 包含项目所有后端API接口的封装，统一处理请求配置、拦截器和错误处理
 */

import axios from 'axios'

/**
 * API 基础配置
 * - 使用相对路径，通过Vite代理转发请求
 */

/**
 * 创建 axios 实例
 * @property {string} baseURL - API基础地址
 * @property {number} timeout - 请求超时时间（600秒）
 * @property {Object} headers - 默认请求头
 */
const api = axios.create({
  baseURL: '/api', // 使用相对路径，通过Vite代理转发请求
  timeout: 600000, // 长时间运行的预测任务需要足够的超时时间（10分钟）
  headers: {
    'Content-Type': 'application/json'
  }
})

/**
 * 请求拦截器
 * - 可用于添加认证信息、请求日志等
 */
api.interceptors.request.use(
  config => {
    // 未来可在此添加token认证逻辑
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

/**
 * 响应拦截器
 * - 统一响应格式处理
 * - 统一错误处理和错误码映射
 */
api.interceptors.response.use(
  response => {
    // 对于blob类型的响应，直接返回完整的response对象，不进行统一格式处理
    if (response.config.responseType === 'blob') {
      return response
    }
    
    // 统一响应格式处理，确保返回数据包含 success、data 和 message 字段
    if (response.data && typeof response.data === 'object') {
      if (!response.data.hasOwnProperty('success')) {
        response.data = {
          success: true,
          data: response.data,
          message: '请求成功'
        }
      }
    }
    return response.data
  },
  error => {
    // 对于blob类型的响应错误，直接返回错误，不进行统一格式处理
    if (error.config?.responseType === 'blob') {
      return Promise.reject(error)
    }
    
    // 统一错误处理，规范化错误信息格式
    let errorMessage = '请求失败'
    let errorCode = 'UNKNOWN_ERROR'
    
    if (error.response) {
      // 服务器返回错误响应
      const status = error.response.status
      const data = error.response.data || {}
      
      errorCode = `HTTP_${status}`
      errorMessage = data.detail || data.message || data.error || `HTTP ${status} 错误`
      
      // 根据HTTP状态码提供更具体的错误信息
      switch (status) {
        case 400: errorMessage = data.detail || data.message || '请求参数错误'; break
        case 401: errorMessage = '未授权访问，请重新登录'; break
        case 403: errorMessage = '权限不足，无法访问该资源'; break
        case 404: errorMessage = '请求的资源不存在'; break
        case 500: errorMessage = '服务器内部错误，请稍后重试'; break
        case 502: errorMessage = '网关错误，后端服务不可用'; break
        case 503: errorMessage = '服务暂时不可用，请稍后重试'; break
      }
    } else if (error.request) {
      // 请求已发送但无响应
      errorCode = 'NETWORK_ERROR'
      errorMessage = '网络连接错误，请检查网络连接'
    } else {
      // 请求配置错误
      errorCode = 'REQUEST_ERROR'
      errorMessage = error.message || '请求配置错误'
    }
    
    // 创建统一的错误对象格式
    const formattedError = {
      success: false,
      error: errorCode,
      message: errorMessage,
      details: error.response?.data?.details || null
    }
    
    console.error(`API错误 [${errorCode}]:`, errorMessage)
    return Promise.reject(formattedError)
  }
)

/**
 * 文件操作相关API
 * 提供文件上传、下载、预览、管理等功能
 */
export const fileApi = {
  /**
   * 上传单个文件
   * @param {File} file - 要上传的文件对象
   * @returns {Promise} 请求Promise
   */
  uploadFile: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  
  /**
   * 批量上传文件
   * @param {Array<File>} files - 文件数组
   * @returns {Promise} 请求Promise
   */
  uploadMultipleFiles: (files) => {
    const formData = new FormData()
    files.forEach((file, index) => {
      formData.append('files', file)
    })
    return api.post('/files/upload-multiple', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  
  /**
   * 批量下载文件（打包成zip）
   * @param {Array<string>} fileIds - 文件ID数组
   * @returns {Promise} 请求Promise
   */
  batchDownloadFiles: (fileIds) => {
    // 使用blob响应类型，以便下载文件
    return api.post('/files/batch-download', { file_ids: fileIds }, {
      responseType: 'blob'
    })
  },
  
  /**
   * 获取文件列表
   * @param {number} page - 页码，默认1
   * @param {number} size - 每页大小，默认10
   * @returns {Promise} 请求Promise
   */
  getFileList: (page = 1, size = 10) => api.get('/files', { params: { page, page_size: size } }),
  
  /**
   * 删除文件
   * @param {string} fileId - 文件ID
   * @returns {Promise} 请求Promise
   */
  deleteFile: (fileId) => api.delete(`/files/${fileId}`),
  
  /**
   * 预览文件内容
   * @param {string} fileId - 文件ID
   * @param {number} page - 页码，默认1
   * @param {number} size - 每页大小，默认20
   * @returns {Promise} 请求Promise
   */
  previewFile: (fileId, page = 1, size = 20) => api.get(`/files/${fileId}/preview`, { params: { page, page_size: size } }),
  
  /**
   * 获取文件详细信息
   * @param {string} fileId - 文件ID
   * @returns {Promise} 请求Promise
   */
  getFileInfo: (fileId) => api.get(`/files/${fileId}`),
  
  /**
   * 获取文件关系
   * @param {string} fileId - 文件ID
   * @returns {Promise} 请求Promise
   */
  getFileRelations: (fileId) => api.get(`/files/${fileId}/related`),
  
  /**
   * 重命名文件
   * @param {string} fileId - 文件ID
   * @param {string} newName - 新文件名
   * @returns {Promise} 请求Promise
   */
  renameFile: (fileId, newName) => api.patch(`/files/${fileId}/rename`, null, { params: { new_name: newName } }),
  
  /**
   * 获取文件原始内容
   * @param {string} fileId - 文件ID
   * @returns {Promise} 请求Promise
   */
  getFileContent: (fileId) => api.get(`/files/${fileId}/raw`)
}

/**
 * 数据预处理相关API
 */
export const preprocessApi = {
  /**
   * 执行数据预处理
   * @param {Object} params - 预处理参数
   * @returns {Promise} 请求Promise
   * @note 与后端路由保持一致，使用无尾斜杠的路径
   */
  preprocessData: (params) => api.post('/preprocess', params)
}

/**
 * 数据分析相关API
 * 提供异常检测、聚类分析、预测等功能
 */
export const analysisApi = {
  /**
   * 检测异常数据
   * @param {Object} params - 异常检测参数
   * @returns {Promise} 请求Promise
   */
  detectAnomalies: (params) => api.post('/analysis/anomaly', params),
  
  /**
   * 提交异常检测任务
   * @param {Object} params - 任务参数
   * @returns {Promise} 请求Promise
   */
  submitAnomalyTask: (params) => api.post('/analysis/anomaly/task', params),
  
  /**
   * 获取异常检测任务状态
   * @param {string} taskId - 任务ID
   * @returns {Promise} 请求Promise
   */
  getAnomalyTaskStatus: (taskId) => api.get(`/analysis/anomaly/task/${taskId}`),
  
  /**
   * 重建/生成散点图数据
   * @param {Object} params - 散点图参数
   * @returns {Promise} 请求Promise
   */
  regenerateScatter: (params) => api.post('/analysis/scatter/regenerate', params),
  
  /**
   * （旧）执行预测分析 - 已废弃占位
   * 建议使用 predictApi 中的模型专用接口
   */
  predict: (params) => api.post('/analysis/predict', params),
  
  /**
   * 执行聚类分析
   * @param {Object} params - 聚类参数
   * @returns {Promise} 请求Promise
   */
  clusterAnalysis: (params) => api.post('/analysis/cluster', params),
  
  /**
   * 估算最优聚类数量K
   * @param {Object} params - 估算参数
   * @returns {Promise} 请求Promise
   */
  estimateOptimalK: (params) => api.post('/analysis/cluster/estimate-k', params)
}

/**
 * 预测分析专用 API（ARIMA / 线性回归 / 随机森林 / XGBoost）
 */
export const predictApi = {
  /**
   * 基于 STL 分解 + 线性回归的时间序列预测（3/4 训练 + 1/4 测试 + 1/8 未来预测）
   * 单地区预测接口路径为 '/predict/stl-reg'，批量预测中的模型 key 为 'stl_reg'
   * @param {{filename: string, area_column: string}} params
   */
  arima: (params) => api.post('/predict/stl-reg', params),

  /**
   * 批量预测（多地区多模型）- 当前仅支持基于 STL + 线性回归的模型（key 为 'stl_reg'）
   * @param {{filename: string, area_columns: string[], models: string[]}} params
   */
  batchPredict: (params) => api.post('/predict/batch-predict', params)
}


/**
 * 模板管理相关API
 */
export const templateApi = {
  /**
   * 获取模板列表
   * @param {string} type - 模板类型（anomaly, cluster, predict）
   * @returns {Promise} 请求Promise
   */
  getTemplates: (type) => api.get('/templates/', { params: { template_type: type } }),
  
  /**
   * 创建模板
   * @param {Object} templateData - 模板数据
   * @returns {Promise} 请求Promise
   */
  createTemplate: (templateData) => api.post('/templates/', templateData),
  
  /**
   * 删除模板
   * @param {number} templateId - 模板ID
   * @returns {Promise} 请求Promise
   */
  deleteTemplate: (templateId) => api.delete(`/templates/${templateId}`),
  
  /**
   * 搜索模板
   * @param {string} type - 模板类型
   * @param {string} keyword - 搜索关键字
   * @returns {Promise} 请求Promise
   */
  searchTemplates: (type, keyword) => api.get(`/templates/search/${type}/`, { params: { keyword } }),
  
  /**
   * 更新模板名称
   * @param {number} templateId - 模板ID
   * @param {string} newName - 新模板名称
   * @returns {Promise} 请求Promise
   */
  updateTemplateName: (templateId, newName) => api.put(`/templates/${templateId}`, { name: newName })
}

/**
 * 系统健康检查API
 */
export const healthApi = {
  /**
   * 检查服务健康状态
   * @returns {Promise<{status: 'healthy'|'unhealthy'}>} 健康状态对象
   */
  checkHealth: () => {
    return api.get('/')
      .then(() => ({ status: 'healthy' }))
      .catch(() => ({ status: 'unhealthy' }))
  }
}

/**
 * 导出默认API对象
 * 包含所有API模块和原始axios实例
 */
export default {
  ...api,      // 导出原始axios实例方法
  file: fileApi,
  preprocess: preprocessApi,
  analysis: analysisApi,
  predictApi,
  health: healthApi,
  template: templateApi
}
