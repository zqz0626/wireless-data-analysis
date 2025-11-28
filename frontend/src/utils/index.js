// 工具函数库 - 提供通用的工具函数

/**
 * 格式化文件大小
 * @param {number} bytes - 文件大小（字节）
 * @returns {string} 格式化后的文件大小
 */
export function formatFileSize(bytes) {
  // 参数验证和边界条件处理
  if (bytes === null || bytes === undefined || isNaN(bytes)) return '0 B';
  if (bytes === 0) return '0 B';
  
  // 确保bytes为数字类型
  const numBytes = Number(bytes);
  if (numBytes < 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  // 使用Math.min确保不会超出数组范围
  const i = Math.min(Math.floor(Math.log(numBytes) / Math.log(k)), sizes.length - 1);
  
  return parseFloat((numBytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 格式化日期时间
 * @param {string|Date} date - 日期时间
 * @returns {string} 格式化后的日期时间
 */
export function formatDateTime(date) {
  // 参数验证
  if (!date) return '未知';
  
  // 处理不同类型的输入
  const d = typeof date === 'string' ? new Date(date.replace(/\s+/, 'T')) : date;
  
  // 日期有效性检查
  if (!(d instanceof Date) || isNaN(d.getTime())) return '无效日期';
  
  try {
    return d.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false // 明确指定24小时制
    });
  } catch (error) {
    console.error('日期格式化失败:', error);
    return '无效日期';
  }
}