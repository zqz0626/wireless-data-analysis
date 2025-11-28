"""
异常检测服务 - 优化版本
当前仅支持 Isolation Forest 算法，用于时间序列/单列数值特征的异常检测。
"""

import pandas as pd
import numpy as np
import os
import logging
import time
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import json

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from .task_manager import task_manager, TaskStatus

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnomalyDetectionService:
    """异常检测服务类"""
    
    def __init__(self):
        # 使用绝对路径确保正确性
        BASE_DIR = Path(__file__).parent.parent.parent
        self.UPLOAD_DIR = BASE_DIR / "uploads"
        self.FILE_DB_PATH = self.UPLOAD_DIR / "file_db.json"
        
        # 确保上传目录存在
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # 算法参数缓存
        self._model_cache: Dict[str, Any] = {}
        
        logger.info(f"异常检测服务初始化完成")
    
    def _load_file_info(self, file_id: str) -> Dict[str, Any]:
        """从文件数据库加载文件信息"""
        if not os.path.exists(self.FILE_DB_PATH):
            raise FileNotFoundError(f"文件数据库不存在: {self.FILE_DB_PATH}")

        with open(self.FILE_DB_PATH, 'r', encoding='utf-8') as f:
            file_db = json.load(f)

        # file_db是一个列表，需要遍历查找
        if isinstance(file_db, list):
            for file_info in file_db:
                if file_info.get('id') == file_id:
                    return file_info
            raise ValueError(f"文件ID不存在: {file_id}")
        else:
            # 如果是字典格式
            if file_id not in file_db:
                raise ValueError(f"文件ID不存在: {file_id}")
            return file_db[file_id]
    
    def _read_file(self, file_path: str, extension: str) -> pd.DataFrame:
        """读取文件并返回DataFrame"""
        logger.info(f"读取文件: {file_path}, 扩展名: {extension}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        try:
            if extension in ['.csv', 'csv']:
                df = pd.read_csv(file_path)
            elif extension in ['.xlsx', '.xls', 'xlsx', 'xls']:
                try:
                    # 优先尝试使用 openpyxl 引擎
                    df = pd.read_excel(file_path, engine='openpyxl')
                except ImportError:
                    raise ValueError("读取Excel需要依赖 openpyxl，请先安装依赖或改用CSV文件")
                except ValueError as ve:
                    # pandas 在引擎不可用时也可能抛出 ValueError
                    msg = str(ve)
                    if 'openpyxl' in msg.lower():
                        raise ValueError("读取Excel需要依赖 openpyxl，请先安装依赖或改用CSV文件")
                    raise
            else:
                raise ValueError(f"不支持的文件格式: {extension}")

            logger.info(f"成功读取文件，数据形状: {df.shape}")
            return df
        except ValueError:
            # 让上层返回 400
            raise
        except Exception as e:
            logger.error(f"读取文件失败: {str(e)}")
            # 其他未知错误归为通用读取失败
            raise ValueError(f"读取文件失败: {str(e)}")
    
    def _prepare_data(self, df: pd.DataFrame, features: List[str]) -> Tuple[pd.DataFrame, np.ndarray]:
        """准备数据用于异常检测"""
        # 如果指定了特征，先过滤到存在于数据中的列；否则使用所有数值列
        if features:
            features = [f for f in features if f in df.columns]
        if not features:
            features = df.select_dtypes(include=[np.number]).columns.tolist()

        if not features:
            raise ValueError("没有可用的数值特征进行异常检测")

        # 提取特征数据，只保留存在的列
        X = df[features].copy()

        # 确保所有列都是数值类型，并且可以转换为float
        numeric_features = []
        for col in X.columns:
            try:
                # 尝试转换为数值类型
                pd.to_numeric(X[col], errors='raise')
                # 检查是否是数值类型
                if pd.api.types.is_numeric_dtype(X[col]):
                    numeric_features.append(col)
            except (ValueError, TypeError):
                # 如果转换失败，跳过这一列
                logger.warning(f"列 '{col}' 无法转换为数值类型，已跳过")
                continue

        if not numeric_features:
            raise ValueError("选择的特征中没有数值类型的列")

        # 只保留数值列
        X = X[numeric_features].copy()

        # 确保所有列都是数值类型
        for col in X.columns:
            X[col] = pd.to_numeric(X[col], errors='coerce')

        # 处理无穷大值
        X = X.replace([np.inf, -np.inf], np.nan)

        # 处理缺失值（使用中位数填充）
        X = X.fillna(X.median())

        # 如果还有NaN（可能整列都是NaN），用0填充
        X = X.fillna(0)

        # 标准化数据
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        if len(X) < 2:
            raise ValueError("样本数量不足，至少需要 2 条样本数据")

        logger.info(f"数据准备完成，特征数: {len(numeric_features)}, 样本数: {len(X)}")
        return X, X_scaled
    
    def detect_isolation_forest(
        self,
        file_id: str,
        features: List[str] = None,
        contamination: float = 0.1,
        n_estimators: int = 100,
        max_samples: str = 'auto',
        random_state: int = 42,
        y_axis_feature: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        使用Isolation Forest进行异常检测（优化版）
        
        Args:
            file_id: 文件ID
            features: 要检测的特征列表
            contamination: 预期异常比例
            n_estimators: 树的数量
            max_samples: 每棵树的样本数
            random_state: 随机种子
        
        Returns:
            包含异常检测结果的字典
        """
        import time
        try:
            import psutil  # 可选依赖，仅用于日志
        except Exception:
            psutil = None
        start_time = time.time()
        
        logger.info(f"开始Isolation Forest异常检测，文件ID: {file_id}")
        if psutil is not None:
            try:
                logger.info(f"当前内存使用: {psutil.virtual_memory().percent}%")
            except Exception:
                logger.info("当前内存使用: N/A")
        
        # 加载文件
        file_info = self._load_file_info(file_id)
        df = self._read_file(file_info['path'], file_info['extension'])
        
        # 准备数据：始终使用用户选择的全部特征进行检测；
        # y_axis_feature 仅用于可视化与插值修正，不限制检测维度。
        selected_features = features
        X, X_scaled = self._prepare_data(df, selected_features)
        feature_names = list(X.columns)
        n_samples = X_scaled.shape[0]

        # 动态调整参数（按样本量统一设置）
        if max_samples == 'auto':
            max_samples_value = min(256, n_samples)  # 限制最大样本数
            if n_samples > 10000:
                n_estimators = min(n_estimators, 50)  # 大数据集减少树数量
        else:
            max_samples_value = max(1, min(int(max_samples), n_samples))

        # 按列独立检测：对每个特征单独建模，并合并异常结果
        combined_scores = np.zeros(n_samples, dtype=float)
        anomaly_mask = np.zeros(n_samples, dtype=bool)
        trigger_features_map: Dict[int, List[str]] = {}

        for col_idx, col_name in enumerate(feature_names):
            # 只使用该列（单特征）进行检测
            X_col = X_scaled[:, [col_idx]]

            model = IsolationForest(
                contamination=max(1e-6, min(float(contamination), 0.5)),
                n_estimators=n_estimators,
                max_samples=max_samples_value,
                random_state=random_state,
                n_jobs=-1
            )

            # 预测异常（-1表示异常，1表示正常）
            predictions_col = model.fit_predict(X_col)

            # 获取异常分数（分数越低越异常）并归一化到0-1
            scores_col = model.score_samples(X_col)
            denom = scores_col.max() - scores_col.min()
            if denom == 0:
                normalized_scores_col = np.zeros_like(scores_col, dtype=float)
            else:
                normalized_scores_col = 1 - (scores_col - scores_col.min()) / denom

            # 汇总该列的异常样本
            anomaly_indices_col = np.where(predictions_col == -1)[0]
            for idx in anomaly_indices_col:
                idx_int = int(idx)
                anomaly_mask[idx_int] = True
                score_val = float(normalized_scores_col[idx_int])
                if score_val > combined_scores[idx_int]:
                    combined_scores[idx_int] = score_val
                trigger_features_map.setdefault(idx_int, []).append(col_name)

            # 更新任务进度（如果提供了 task_id）
            if task_id is not None:
                try:
                    progress = float(col_idx + 1) / max(len(feature_names), 1)
                    task_manager.update(task_id, status=TaskStatus.RUNNING, progress=progress)
                except Exception:
                    # 进度更新失败不影响主流程
                    pass

        # 汇总所有列的异常样本索引
        anomaly_indices = np.where(anomaly_mask)[0]
        
        try:
            mem_str = f"内存峰值: {psutil.virtual_memory().percent}%，" if 'psutil' in globals() and psutil is not None else ""
        except Exception:
            mem_str = ""
        logger.info(
            f"异常检测完成，耗时 {time.time()-start_time:.2f}s，" +
            mem_str +
            f"发现异常: {len(anomaly_indices)} 个"
        )
        
        # 基于检测结果对指定 Y 轴特征做插值修正并生成新文件
        corrected_file_path, corrected_filename = self._save_corrected_anomaly_file(
            df=df,
            file_info=file_info,
            anomaly_indices=anomaly_indices,
            y_axis_feature=y_axis_feature,
            trigger_features_map=trigger_features_map,
        )

        result = self._format_results(
            df=df,
            anomaly_indices=anomaly_indices,
            scores=combined_scores,
            features=features or X.columns.tolist(),
            method='isolation_forest',
            y_axis_feature=y_axis_feature,
            trigger_features_map=trigger_features_map,
        )

        # 将修正后文件的信息附加到结果中，便于前端或后续处理使用
        result['corrected_file'] = {
            'path': corrected_file_path,
            'filename': corrected_filename,
        } if corrected_file_path is not None else None

        return result
    
    def _safe_float(self, value: Any) -> float:
        """安全地转换为浮点数，处理NaN和Inf"""
        if pd.isna(value):
            return 0.0
        if isinstance(value, (np.integer, np.floating)):
            value = float(value)
        if isinstance(value, float):
            if np.isinf(value):
                return 999999.0 if value > 0 else -999999.0
            if np.isnan(value):
                return 0.0
        return float(value)

    def _detect_timestamp_column(self, df: pd.DataFrame) -> Optional[str]:
        """尝试自动识别时间戳列"""
        if df is None or df.empty:
            return None

        cols = list(df.columns)
        if not cols:
            return None

        lower_map = {c: str(c).lower() for c in cols}

        # 1) 根据列名匹配常见时间字段，排除类似 "unnamed" 的索引列
        name_keywords = ['timestamp', 'time', 'datetime', 'date']
        for key in name_keywords:
            for col in cols:
                name = lower_map.get(col, '')
                if key in name and 'unnamed' not in name:
                    return col

        # 2) 已经是 datetime 类型的列
        try:
            datetime_cols = df.select_dtypes(include=['datetime64[ns]', 'datetimetz']).columns.tolist()
        except TypeError:
            # pandas 在解析类似 "[ns, tz]" 的字符串时会抛出 TypeError，这里退回空列表
            datetime_cols = []
        for col in datetime_cols:
            name = lower_map.get(col, '')
            if 'unnamed' not in name:
                return col

        # 3) 尝试将非数值列解析为 datetime，按成功率选择最优列
        #    这里也允许 "unnamed" 列参与判断，以适配类似索引列中实际存时间的情况
        best_col = None
        best_ratio = 0.0
        for col in cols:
            name = lower_map.get(col, '')
            s = df[col]
            if pd.api.types.is_numeric_dtype(s):
                continue
            try:
                converted = pd.to_datetime(s, errors='coerce', infer_datetime_format=True)
                ratio = converted.notna().mean()
            except Exception:
                continue
            if ratio >= 0.8 and ratio > best_ratio:
                best_ratio = ratio
                best_col = col
        if best_col is not None:
            return best_col

        # 4) 兜底：返回第一个非 "unnamed" 列
        for col in cols:
            name = lower_map.get(col, '')
            if 'unnamed' not in name:
                return col

        return None

    def _format_results(
        self,
        df: pd.DataFrame,
        anomaly_indices: np.ndarray,
        scores: np.ndarray,
        features: List[str],
        method: str,
        y_axis_feature: Optional[str] = None,
        trigger_features_map: Optional[Dict[int, List[str]]] = None,
    ) -> Dict[str, Any]:
        """格式化异常检测结果"""
        anomalies = []
        feature_anomaly_map: Dict[str, List[int]] = {}

        # 识别时间戳列：优先认为第一列为时间戳列
        timestamp_col = self._detect_timestamp_column(df)

        # 解析基准时间（第一行第一列）用于计算后续时间戳
        base_time = None
        if timestamp_col is not None and timestamp_col in df.columns and len(df) > 0:
            try:
                base_time_str = str(df.iloc[0][timestamp_col])
                base_time = pd.to_datetime(base_time_str)
            except Exception as e:
                logger.warning(f"无法解析基准时间戳: {e}")
                base_time = None

        for idx in anomaly_indices:
            idx_int = int(idx)

            # 确定严重程度
            score = self._safe_float(scores[idx_int])
            if score >= 0.8:
                severity = '高'
            elif score >= 0.5:
                severity = '中'
            else:
                severity = '低'

            # 提取该行的特征值（排除时间戳列）
            feature_values = {}
            for feature in features:
                # 跳过时间戳列，避免把时间字符串当数值
                if feature == timestamp_col:
                    continue
                value = df.iloc[idx_int][feature]
                # 安全转换为浮点数
                feature_values[feature] = self._safe_float(value)

            # 计算该行的时间戳：基准时间 + 行号 * 10分钟
            calculated_ts = None
            if timestamp_col is not None and timestamp_col in df.columns:
                try:
                    ts_raw = df.iloc[idx_int][timestamp_col]
                    ts_parsed = pd.to_datetime(ts_raw)
                    calculated_ts = ts_parsed
                except Exception as e:
                    logger.warning(f"计算时间戳失败（idx={idx}）: {e}")
                    calculated_ts = None

            # 触发该异常的特征列表（如果提供了按列检测信息）
            trigger_feats = None
            if trigger_features_map is not None:
                trigger_feats = trigger_features_map.get(idx_int, [])
                if trigger_feats:
                    for feat in trigger_feats:
                        if feat is None:
                            continue
                        feature_anomaly_map.setdefault(str(feat), []).append(idx_int)

            anomaly = {
                'id': f'A-{len(anomalies) + 1}',
                'row_index': idx_int,
                'severity': severity,
                'score': score,
                'feature_values': feature_values,
                'description': f'检测到{severity}级别异常，异常分数为{score:.4f}',
                'timestamp': None if calculated_ts is None else calculated_ts.isoformat(),
                'trigger_features': trigger_feats,
            }
            anomalies.append(anomaly)

        # 按分数排序
        anomalies.sort(key=lambda x: x['score'], reverse=True)

        # 生成散点图数据（支持二维/三维特征）
        scatter_plot_data = self._generate_scatter_plot_data(
            df,
            anomaly_indices,
            features,
            y_axis_feature=y_axis_feature,
            trigger_features_map=trigger_features_map,
        )

        result = {
            'total_samples': len(df),
            'anomaly_count': len(anomalies),
            'anomaly_percentage': round((len(anomalies) / len(df) * 100), 2) if len(df) > 0 else 0.0,
            'method': method,
            'features': features,
            'anomalies': anomalies,
            'scatter_plot': scatter_plot_data,
            'feature_anomalies': feature_anomaly_map,
        }

        logger.info(f"异常检测完成，发现 {len(anomalies)} 个异常样本")
        return result

    def _generate_scatter_plot_data(
        self,
        df: pd.DataFrame,
        anomaly_indices: np.ndarray,
        features: List[str],
        y_axis_feature: Optional[str] = None,
        trigger_features_map: Optional[Dict[int, List[str]]] = None,
    ) -> Dict[str, Any]:
        """生成按时间维度的散点图数据

        - 横坐标：第一列时间戳
        - 纵坐标：数值特征（优先使用选中的第一个数值特征）
        - 输出正常点与异常点，前端可将异常点标红
        """

        # 确定时间戳列：默认使用第一列
        timestamp_col = self._detect_timestamp_column(df)

        if timestamp_col is None or timestamp_col not in df.columns:
            return {'error': '未找到时间戳列，无法生成时间散点图'}

        # 选择一个数值特征作为Y轴
        # 1) 若显式指定了 y_axis_feature，且为数值列，则优先使用
        y_feature: Optional[str] = None
        if y_axis_feature and y_axis_feature in df.columns:
            if y_axis_feature != timestamp_col and pd.api.types.is_numeric_dtype(df[y_axis_feature]):
                y_feature = y_axis_feature

        # 2) 否则，优先使用 features 中的第一个数值列
        if y_feature is None:
            candidate_features = features or df.select_dtypes(include=[np.number]).columns.tolist()
            for f in candidate_features:
                if f == timestamp_col:
                    continue
                if f in df.columns and pd.api.types.is_numeric_dtype(df[f]):
                    y_feature = f
                    break

        if y_feature is None:
            return {'error': '未找到可用于Y轴的数值特征'}

        # 异常索引集合，便于快速判断
        anomaly_set = set(int(i) for i in anomaly_indices.tolist())

        normal_points = []
        anomaly_points = []
        corrected_points = []
        corrected_anomaly_points = []

        # 基于异常点进行插值改正：
        # 1. 将异常位置的数值设为 NaN
        # 2. 对整列做线性插值，再前向/后向填充
        # 3. 用插值后的数值生成一套“改正后”的散点数据
        try:
            y_series = pd.to_numeric(df[y_feature], errors='coerce')
            y_corrected = y_series.copy()
            if anomaly_set:
                # 只在索引范围内设置 NaN，避免越界
                max_idx = len(y_corrected) - 1
                corrected_indices = [i for i in anomaly_set if 0 <= i <= max_idx]
                if corrected_indices:
                    y_corrected.iloc[corrected_indices] = np.nan
            y_interp = y_corrected.interpolate(method='linear').ffill().bfill()
        except Exception:
            # 插值失败时，退回使用原始数值，确保接口可用
            y_interp = pd.to_numeric(df[y_feature], errors='coerce')

        for idx, row in df.iterrows():
            # 解析时间戳为 ISO 字符串，前端可直接作为时间轴使用
            ts_raw = row[timestamp_col]
            try:
                ts_parsed = pd.to_datetime(ts_raw)
                ts_iso = ts_parsed.isoformat()
            except Exception:
                # 解析失败时退回原始字符串
                ts_iso = str(ts_raw)

            value = self._safe_float(row[y_feature])
            # 对应位置的插值后数值
            try:
                corrected_value = self._safe_float(y_interp.iloc[int(idx)])
            except Exception:
                corrected_value = value

            idx_int = int(idx)

            point = {
                'time': ts_iso,
                'value': value,
                'row_index': idx_int
            }
            corrected_point = {
                'time': ts_iso,
                'value': corrected_value,
                'row_index': idx_int
            }

            is_anomaly = idx_int in anomaly_set

            # 如果提供了按列触发信息，则仅当当前 Y 轴特征在触发列表中时，才在该视图中视为异常
            if is_anomaly and trigger_features_map is not None and y_feature is not None:
                triggers = trigger_features_map.get(idx_int, [])
                if y_feature not in triggers:
                    is_anomaly = False

            if is_anomaly:
                anomaly_points.append(point)
                corrected_anomaly_points.append(corrected_point)
            else:
                normal_points.append(point)
            corrected_points.append(corrected_point)

        # 处理横轴标签：如果列名为空或类似 "unnamed"，统一显示为 "时间"
        x_label = str(timestamp_col) if timestamp_col is not None else ''
        if not x_label.strip() or 'unnamed' in x_label.lower():
            x_label = '时间'

        scatter_data = {
            'x_label': x_label,
            'y_label': y_feature,
            'normal_points': normal_points,
            'anomaly_points': anomaly_points,
            'total_points': len(df),
            'anomaly_count': len(anomaly_points),
            # 新增：基于插值改正后的散点数据
            'corrected_points': corrected_points,
            'corrected_anomaly_points': corrected_anomaly_points
        }

        return scatter_data

    def generate_scatter_from_files(
        self,
        base_file_id: str,
        corrected_file_path: str,
        y_axis_feature: str,
        anomaly_indices: List[int],
    ) -> Dict[str, Any]:
        """从已有的原始文件和修正后文件重新构建指定 Y 轴特征的散点图数据。

        不重新执行异常检测，仅使用给定的异常行索引列表来区分异常点。
        """

        if not y_axis_feature:
            raise ValueError("y_axis_feature 不能为空")

        if not corrected_file_path:
            raise ValueError("corrected_file_path 不能为空")

        corrected_path = Path(os.path.abspath(corrected_file_path))
        if not corrected_path.exists():
            raise FileNotFoundError(f"修正后文件不存在: {corrected_file_path}")

        # 加载原始文件
        file_info = self._load_file_info(base_file_id)
        df_base = self._read_file(file_info['path'], file_info['extension'])

        if y_axis_feature not in df_base.columns:
            raise ValueError(f"Y 轴特征列 '{y_axis_feature}' 不存在于原始文件中")

        # 自动识别时间列，仅使用原始文件
        timestamp_col = self._detect_timestamp_column(df_base)

        anomaly_set = set(int(i) for i in (anomaly_indices or []))

        # 构建改正序列：对异常行置 NaN 后插值、前后填充
        base_series = pd.to_numeric(df_base[y_axis_feature], errors='coerce')
        corrected_series = base_series.copy()
        if anomaly_set:
            idx_list = [i for i in anomaly_set if 0 <= i < len(corrected_series)]
            if idx_list:
                corrected_series.iloc[idx_list] = np.nan
        corrected_series = corrected_series.interpolate(method='linear').ffill().bfill()

        normal_points: List[Dict[str, Any]] = []
        anomaly_points: List[Dict[str, Any]] = []
        corrected_points: List[Dict[str, Any]] = []
        corrected_anomaly_points: List[Dict[str, Any]] = []

        n = len(df_base)
        for idx_int in range(n):
            row_base = df_base.iloc[idx_int]

            # 时间戳
            if timestamp_col is not None and timestamp_col in df_base.columns:
                ts_value = row_base.get(timestamp_col)
            else:
                ts_value = idx_int

            # 转为 ISO 字符串，尽量与原有逻辑保持一致
            try:
                if isinstance(ts_value, (pd.Timestamp, np.datetime64)):
                    ts_iso = pd.to_datetime(ts_value).isoformat()
                else:
                    ts_iso = str(ts_value)
            except Exception:
                ts_iso = str(ts_value)

            v_base = row_base.get(y_axis_feature)
            v_corr = corrected_series.iloc[idx_int]

            if pd.isna(v_base) or pd.isna(v_corr):
                continue

            point = {
                'time': ts_iso,
                'value': self._safe_float(v_base),
                'row_index': idx_int,
            }
            corrected_point = {
                'time': ts_iso,
                'value': self._safe_float(v_corr),
                'row_index': idx_int,
            }

            if idx_int in anomaly_set:
                anomaly_points.append(point)
                corrected_anomaly_points.append(corrected_point)
            else:
                normal_points.append(point)
            corrected_points.append(corrected_point)

        # 处理横轴标签
        x_label = str(timestamp_col) if timestamp_col is not None else ''
        if not x_label.strip() or 'unnamed' in x_label.lower():
            x_label = '时间'

        scatter_data = {
            'x_label': x_label,
            'y_label': y_axis_feature,
            'normal_points': normal_points,
            'anomaly_points': anomaly_points,
            'total_points': len(df_base),
            'anomaly_count': len(anomaly_points),
            'corrected_points': corrected_points,
            'corrected_anomaly_points': corrected_anomaly_points,
        }

        return scatter_data

    def _save_corrected_anomaly_file(
        self,
        df: pd.DataFrame,
        file_info: Dict[str, Any],
        anomaly_indices: np.ndarray,
        y_axis_feature: Optional[str],
        trigger_features_map: Optional[Dict[int, List[str]]],
    ) -> Tuple[Optional[str], Optional[str]]:
        """根据异常结果对 Y 轴特征做插值修正并生成新文件。

        仅在 y_axis_feature 合法且为数值列时生效；否则返回 (None, None)。
        """

        try:
            if not y_axis_feature or y_axis_feature not in df.columns:
                return None, None

            corrected_df = df.copy()

            # 构建需要插值的列集合：当前 Y 轴特征 + 触发异常的其它列
            columns_to_fix = set()
            if trigger_features_map:
                for feats in trigger_features_map.values():
                    columns_to_fix.update(feats)
            columns_to_fix.add(y_axis_feature)

            if not columns_to_fix:
                return None, None

            anomaly_set = set(int(i) for i in anomaly_indices.tolist())

            for col in columns_to_fix:
                if col not in df.columns:
                    continue
                if not pd.api.types.is_numeric_dtype(df[col]):
                    continue

                if trigger_features_map:
                    indices = [
                        int(i)
                        for i in anomaly_indices.tolist()
                        if col in trigger_features_map.get(int(i), [])
                    ]
                else:
                    indices = list(anomaly_set)

                if not indices:
                    continue

                series = pd.to_numeric(df[col], errors='coerce')
                corrected = series.copy()
                max_idx = len(corrected) - 1
                valid_indices = [i for i in indices if 0 <= i <= max_idx]
                if not valid_indices:
                    continue
                corrected.iloc[valid_indices] = np.nan
                corrected = corrected.interpolate(method='linear').ffill().bfill()
                corrected_df[col] = corrected

            # 生成新的文件名：在原始文件名后追加 _anomaly，如有重复则追加 (数字)
            original_path = file_info.get('path')
            if not original_path:
                return None, None

            original_path_obj = Path(os.path.abspath(original_path))
            parent_dir = original_path_obj.parent
            base_name = original_path_obj.stem  # 不含扩展名
            extension = original_path_obj.suffix  # 包含点，例如 .csv

            safe_base = f"{base_name}_anomaly"
            candidate = parent_dir / f"{safe_base}{extension}"
            counter = 1
            while candidate.exists():
                candidate = parent_dir / f"{safe_base}({counter}){extension}"
                counter += 1

            # 根据原始扩展名选择保存格式
            ext_lower = extension.lower().lstrip('.')
            if ext_lower == 'csv':
                corrected_df.to_csv(candidate, index=False)
            elif ext_lower in ('xlsx', 'xls'):
                corrected_df.to_excel(candidate, index=False)
            else:
                # 兜底：保存为 CSV
                candidate = candidate.with_suffix('.csv')
                corrected_df.to_csv(candidate, index=False)

            # 将新文件登记到 file_db，并继承原文件的 GeoJSON 关联
            try:
                self._register_corrected_file_in_db(
                    parent_file_info=file_info,
                    new_path=str(candidate),
                    extension=ext_lower if ext_lower in ('csv', 'xlsx', 'xls') else 'csv',
                )
            except Exception as e:
                logger.error(f"登记插值修正文件到 file_db 失败: {e}")

            logger.info(f"已保存插值修正后的异常文件: {candidate}")
            return str(candidate), candidate.name
        except Exception as e:
            logger.error(f"保存插值修正后的文件失败: {e}")
            return None, None

    def _register_corrected_file_in_db(
        self,
        parent_file_info: Dict[str, Any],
        new_path: str,
        extension: str,
    ) -> None:
        """将新生成的异常修正文件登记到 file_db.json 中，并继承父文件的关联信息。

        - id: 使用去扩展名后的文件名
        - parent_file_id: 继承父文件 id
        - related_geojson_id: 如果父文件有则继承
        """

        try:
            file_db_path = self.FILE_DB_PATH
            records: Any = []
            if os.path.exists(file_db_path):
                with open(file_db_path, 'r', encoding='utf-8') as f:
                    try:
                        records = json.load(f) or []
                    except Exception:
                        records = []

            if not isinstance(records, list):
                # 为简单起见，仅处理列表结构
                records = []

            new_path_abs = os.path.abspath(new_path)
            basename = os.path.basename(new_path_abs)
            file_id = os.path.splitext(basename)[0]

            # 如果已存在相同 path 的记录，则不重复登记
            for r in records:
                if os.path.abspath(str(r.get('path', ''))) == new_path_abs:
                    return

            size = 0
            try:
                size = os.path.getsize(new_path_abs)
            except Exception:
                pass

            record = {
                "id": file_id,
                "original_filename": basename,
                "filename": basename,
                "path": new_path_abs,
                "size": size,
                "upload_time": pd.Timestamp.now().isoformat(),
                "extension": extension,
                "file_type": "data",
                "parent_file_id": parent_file_info.get("id"),
            }

            # 继承父文件的 GeoJSON 关联
            related_geojson_id = parent_file_info.get("related_geojson_id")
            if related_geojson_id:
                record["related_geojson_id"] = related_geojson_id

            records.append(record)

            # 回写 file_db.json
            with open(file_db_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)

            logger.info(f"已将修正文件登记到 file_db: id={file_id}")
        except Exception as e:
            logger.error(f"_register_corrected_file_in_db 失败: {e}")

# 创建全局服务实例
anomaly_service = AnomalyDetectionService()
