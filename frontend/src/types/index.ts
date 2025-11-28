// 类型定义文件 - 增强代码类型安全

// 文件信息接口
export interface FileInfo {
  id: string;
  original_filename: string;
  size: number;
  extension: string;
  upload_time: string;
  row_count?: number;
  column_count?: number;
  file_path?: string;
}

// 异常检测配置接口
export interface AnomalyDetectionConfig {
  method: 'isolation_forest' | 'one_class_svm' | 'lof';
  contamination: number;
  targetFeature: string[];
  parameters?: Record<string, any>;
}

// 异常检测结果接口
export interface AnomalyDetectionResult {
  file_id: string;
  method: string;
  contamination: number;
  anomaly_count: number;
  total_samples: number;
  anomaly_indices: number[];
  anomaly_scores?: number[];
  execution_time: number;
  features_used: string[];
}

// API响应接口
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// 预处理配置接口
export interface PreprocessConfig {
  operation: 'drop_null' | 'fill_null' | 'standardize' | 'one_hot_encode';
  parameters: Record<string, any>;
}

// 预处理结果接口
export interface PreprocessResult {
  file_id: string;
  operation: string;
  parameters: Record<string, any>;
  result_file_id: string;
  execution_time: number;
  statistics?: Record<string, any>;
}

// 上传文件响应接口
export interface UploadResponse {
  file_id: string;
  original_filename: string;
  size: number;
  extension: string;
  upload_time: string;
}

// 错误处理接口
export interface ErrorInfo {
  code: string;
  message: string;
  details?: any;
}

// 加载状态接口
export interface LoadingState {
  isLoading: boolean;
  message?: string;
  progress?: number;
}