// 测试API连接
import api from './index.js'

console.log('测试API连接...')
console.log('API基础地址:', api.defaults.baseURL)

// 测试根路径
api.get('/')
  .then(response => {
    console.log('根路径测试成功:', response)
  })
  .catch(error => {
    console.error('根路径测试失败:', error)
  })

// 测试健康检查
api.get('/health')
  .then(response => {
    console.log('健康检查测试成功:', response)
  })
  .catch(error => {
    console.error('健康检查测试失败:', error)
  })

// 测试模板API
api.get('/api/templates')
  .then(response => {
    console.log('模板列表测试成功:', response)
  })
  .catch(error => {
    console.error('模板列表测试失败:', error)
  })