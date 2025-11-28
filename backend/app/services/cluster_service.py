"""
聚类分析服务
提供多种聚类算法的实现和评估功能
"""
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
from typing import Dict, Any, List, Optional, Union, Tuple
import logging
import time
import os
import json
from pathlib import Path
from ..config.settings import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def safe_float(value: Any) -> Optional[float]:
    """将输入安全转换为 Python float。

    如果值为 NaN 或无穷大，则返回 None，避免 JSON 序列化报
    "Out of range float values are not JSON compliant"。
    """
    try:
        v = float(value)
    except Exception:
        return None
    if np.isnan(v) or np.isinf(v):
        return None
    return v


class ClusterService:
    """聚类分析服务类"""
    
    def __init__(self):
        """初始化聚类服务"""
        self.upload_dir = Path(settings.UPLOAD_DIR)
        logger.info("聚类分析服务初始化完成")
    
    def _load_data(self, file_id: str) -> pd.DataFrame:
        """
        加载数据文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            DataFrame: 加载的数据
        """
        # 从file_router导入file_db
        from ..api.file_router import file_db
        
        # 查找文件信息
        file_info = next((f for f in file_db if f["id"] == file_id), None)
        if not file_info:
            raise FileNotFoundError(f"文件不存在: {file_id}")
        
        file_path = Path(file_info["path"])
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件已被删除: {file_id}")
        
        # 根据文件扩展名选择读取方法
        if file_path.suffix.lower() == '.csv':
            df = pd.read_csv(file_path)
        elif file_path.suffix.lower() in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_path.suffix}")
        
        logger.info(f"成功加载数据文件: {file_id}, 形状: {df.shape}")
        return df
    
    def _prepare_data(
        self,
        df: pd.DataFrame,
        features: List[str],
        standardize: bool = False
    ) -> tuple:
        """
        准备聚类数据
        
        Args:
            df: 原始数据
            features: 特征列表
            standardize: 是否标准化
            
        Returns:
            tuple: (处理后的数据, 缩放器)
        """
        # 选择特征
        if not features:
            # 如果没有指定特征，使用所有数值列
            features = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # 检查特征是否存在
        missing_features = [f for f in features if f not in df.columns]
        if missing_features:
            raise ValueError(f"以下特征不存在: {missing_features}")
        
        # 提取特征数据
        X = df[features].copy()
        
        # 处理缺失值
        if X.isnull().any().any():
            logger.warning("数据中存在缺失值，使用均值填充")
            X = X.fillna(X.mean())
        
        # 标准化
        scaler = None
        if standardize:
            scaler = StandardScaler()
            X = pd.DataFrame(
                scaler.fit_transform(X),
                columns=features,
                index=X.index
            )
            logger.info("数据已标准化")
        
        return X, scaler

    def _prepare_region_data(
        self,
        df: pd.DataFrame,
        features: List[str],
        standardize: bool = False
    ) -> tuple:
        """按地区聚类时的数据准备：

        将每个地区列视为一个样本，整条时间序列作为其特征向量。
        结果矩阵 X 的行索引为地区名，列为时间索引（或生成的序号）。
        """
        # 选择特征列（地区列）
        if not features:
            # 如果没有指定特征，使用所有数值列
            features = df.select_dtypes(include=[np.number]).columns.tolist()

        # 检查特征是否存在
        missing_features = [f for f in features if f not in df.columns]
        if missing_features:
            raise ValueError(f"以下特征不存在: {missing_features}")

        # 提取地区列并转置：行=地区，列=时间
        region_df = df[features].copy()

        # 缺失值按列均值填充
        if region_df.isnull().any().any():
            logger.warning("按地区聚类：数据中存在缺失值，使用均值填充")
            region_df = region_df.fillna(region_df.mean())

        X = region_df.T  # 现在行是地区，列是时间

        # 为列创建统一的名称，避免时间列类型不一致
        X.columns = [f"t_{i}" for i in range(X.shape[1])]

        scaler = None
        if standardize:
            scaler = StandardScaler()
            X_values = scaler.fit_transform(X.values)
            X = pd.DataFrame(X_values, index=X.index, columns=X.columns)
            logger.info("按地区聚类：数据已标准化")

        return X, scaler
    
    def _apply_dimensionality_reduction(
        self,
        X: pd.DataFrame,
        method: str = 'none',
        n_components: int = 2
    ) -> pd.DataFrame:
        """
        应用降维
        
        Args:
            X: 输入数据
            method: 降维方法 ('none', 'pca', 'tsne')
            n_components: 降维后的维度
            
        Returns:
            降维后的数据
        """
        if method == 'none' or method is None:
            return X
        
        if method == 'pca':
            pca = PCA(n_components=min(n_components, X.shape[1]))
            X_reduced = pca.fit_transform(X)
            logger.info(f"PCA降维完成，解释方差比: {pca.explained_variance_ratio_.sum():.4f}")
            return pd.DataFrame(
                X_reduced,
                columns=[f'PC{i+1}' for i in range(X_reduced.shape[1])],
                index=X.index
            )
        else:
            raise ValueError(f"不支持的降维方法: {method}")
    
    def kmeans_clustering(
        self,
        file_id: str,
        features: List[str],
        n_clusters: int = 3,
        max_iter: int = 300,
        random_state: int = 42,
        standardize: bool = False,
        dimensionality_reduction: str = 'none',
        pca_components: int = 20,
    ) -> Dict[str, Any]:
        """
        K-means聚类
        
        Args:
            file_id: 文件ID
            features: 特征列表
            n_clusters: 聚类数量
            max_iter: 最大迭代次数
            random_state: 随机种子
            standardize: 是否标准化
            dimensionality_reduction: 降维方法
            pca_components: PCA维度
            
        Returns:
            聚类结果
        """
        start_time = time.time()
        
        # 加载和准备数据
        df = self._load_data(file_id)
        X, scaler = self._prepare_region_data(df, features, standardize)
        
        # 降维
        X_for_clustering = self._apply_dimensionality_reduction(
            X, dimensionality_reduction, pca_components
        )
        
        # 执行K-means聚类
        kmeans = KMeans(
            n_clusters=n_clusters,
            max_iter=max_iter,
            random_state=random_state,
            n_init=10
        )
        labels = kmeans.fit_predict(X_for_clustering)
        
        # 计算评估指标
        silhouette = silhouette_score(X_for_clustering, labels)
        davies_bouldin = davies_bouldin_score(X_for_clustering, labels)
        calinski_harabasz = calinski_harabasz_score(X_for_clustering, labels)
        
        # 生成聚类分布
        cluster_distribution = self._generate_cluster_distribution(
            X, labels, n_clusters, kmeans.cluster_centers_ if dimensionality_reduction == 'none' else None
        )
        
        execution_time = time.time() - start_time
        
        result = {
            'algorithm': 'kmeans',
            'n_clusters': n_clusters,
            'labels': labels.tolist(),
            'cluster_centers': kmeans.cluster_centers_.tolist() if dimensionality_reduction == 'none' else None,
            'inertia': safe_float(kmeans.inertia_),
            'silhouette_score': safe_float(silhouette),
            'davies_bouldin_score': safe_float(davies_bouldin),
            'calinski_harabasz_score': safe_float(calinski_harabasz),
            'cluster_distribution': cluster_distribution,
            'total_samples': len(labels),
            'objects': list(X.index),
            'execution_time': safe_float(execution_time),
            'features': features,
            'n_iterations': int(kmeans.n_iter_)
        }

        self._attach_time_trend_metadata(result, df, labels, list(X.index))
        logger.info(f"K-means聚类完成，轮廓系数: {silhouette:.4f}")
        return result
    
    def hierarchical_clustering(
        self,
        file_id: str,
        features: List[str],
        n_clusters: int = 3,
        linkage: str = 'ward',
        random_state: int = 42,
        standardize: bool = False,
        dimensionality_reduction: str = 'none',
        pca_components: int = 2,
    ) -> Dict[str, Any]:
        """
        层次聚类
        
        Args:
            file_id: 文件ID
            features: 特征列表
            n_clusters: 聚类数量
            linkage: 链接方式
            random_state: 随机种子
            standardize: 是否标准化
            dimensionality_reduction: 降维方法
            pca_components: PCA维度
            
        Returns:
            聚类结果
        """
        start_time = time.time()
        
        # 加载和准备数据
        df = self._load_data(file_id)
        X, scaler = self._prepare_region_data(df, features, standardize)
        
        # 降维
        X_for_clustering = self._apply_dimensionality_reduction(
            X, dimensionality_reduction, pca_components
        )
        
        # 执行层次聚类
        hierarchical = AgglomerativeClustering(
            n_clusters=n_clusters,
            linkage=linkage
        )
        labels = hierarchical.fit_predict(X_for_clustering)
        
        # 计算评估指标
        silhouette = silhouette_score(X_for_clustering, labels)
        davies_bouldin = davies_bouldin_score(X_for_clustering, labels)
        calinski_harabasz = calinski_harabasz_score(X_for_clustering, labels)
        
        # 生成聚类分布
        cluster_distribution = self._generate_cluster_distribution(X, labels, n_clusters)
        
        execution_time = time.time() - start_time
        
        result = {
            'algorithm': 'hierarchical',
            'n_clusters': n_clusters,
            'linkage': linkage,
            'labels': labels.tolist(),
            'silhouette_score': safe_float(silhouette),
            'davies_bouldin_score': safe_float(davies_bouldin),
            'calinski_harabasz_score': safe_float(calinski_harabasz),
            'cluster_distribution': cluster_distribution,
            'total_samples': len(labels),
            'objects': list(X.index),
            'execution_time': safe_float(execution_time),
            'features': features
        }

        self._attach_time_trend_metadata(result, df, labels, list(X.index))
        logger.info(f"层次聚类完成，轮廓系数: {silhouette:.4f}")
        return result
    
    def gmm_clustering(
        self,
        file_id: str,
        features: List[str],
        n_clusters: int = 3,
        covariance_type: str = 'full',
        random_state: int = 42,
        standardize: bool = False,
        dimensionality_reduction: str = 'none',
        pca_components: int = 2,
    ) -> Dict[str, Any]:
        """
        高斯混合模型聚类
        
        Args:
            file_id: 文件ID
            features: 特征列表
            n_clusters: 聚类数量
            covariance_type: 协方差类型
            random_state: 随机种子
            standardize: 是否标准化
            dimensionality_reduction: 降维方法
            pca_components: PCA维度
            
        Returns:
            聚类结果
        """
        start_time = time.time()
        
        # 加载和准备数据（按地区聚类，与 KMeans/层次聚类保持一致）
        df = self._load_data(file_id)
        X, scaler = self._prepare_region_data(df, features, standardize)
        
        # 降维
        X_for_clustering = self._apply_dimensionality_reduction(
            X, dimensionality_reduction, pca_components
        )
        
        # 执行GMM聚类
        gmm = GaussianMixture(
            n_components=n_clusters,
            covariance_type=covariance_type,
            random_state=random_state,
            n_init=10
        )
        labels = gmm.fit_predict(X_for_clustering)
        
        # 计算评估指标
        silhouette = silhouette_score(X_for_clustering, labels)
        davies_bouldin = davies_bouldin_score(X_for_clustering, labels)
        calinski_harabasz = calinski_harabasz_score(X_for_clustering, labels)
        
        # 生成聚类分布
        cluster_distribution = self._generate_cluster_distribution(X, labels, n_clusters)
        
        execution_time = time.time() - start_time
        
        result = {
            'algorithm': 'gmm',
            'n_clusters': n_clusters,
            'covariance_type': covariance_type,
            'labels': labels.tolist(),
            'silhouette_score': safe_float(silhouette),
            'davies_bouldin_score': safe_float(davies_bouldin),
            'calinski_harabasz_score': safe_float(calinski_harabasz),
            'bic': safe_float(gmm.bic(X_for_clustering)),
            'aic': safe_float(gmm.aic(X_for_clustering)),
            'cluster_distribution': cluster_distribution,
            'total_samples': len(labels),
            'objects': list(X.index),
            'execution_time': safe_float(execution_time),
            'features': features,
            'converged': bool(gmm.converged_)
        }

        self._attach_time_trend_metadata(result, df, labels, list(X.index))
        logger.info(f"GMM聚类完成，轮廓系数: {silhouette:.4f}")
        return result
    
    def estimate_optimal_k(
        self,
        file_id: str,
        features: List[str],
        k_range: tuple = (2, 10),
        standardize: bool = False
    ) -> Dict[str, Any]:
        """
        估计最佳K值
        
        Args:
            file_id: 文件ID
            features: 特征列表
            k_range: K值范围
            standardize: 是否标准化
            
        Returns:
            K值估计结果
        """
        start_time = time.time()
        
        # 加载和准备数据
        df = self._load_data(file_id)
        X, scaler = self._prepare_region_data(df, features, standardize)
        
        results = []
        k_min, k_max = k_range
        
        for k in range(k_min, k_max + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)
            
            silhouette = silhouette_score(X, labels)
            davies_bouldin = davies_bouldin_score(X, labels)
            calinski_harabasz = calinski_harabasz_score(X, labels)
            
            results.append({
                'k': k,
                'inertia': float(kmeans.inertia_),
                'silhouette_score': float(silhouette),
                'davies_bouldin_score': float(davies_bouldin),
                'calinski_harabasz_score': float(calinski_harabasz)
            })
        
        # 找出推荐的K值（基于轮廓系数）
        best_k = max(results, key=lambda x: x['silhouette_score'])['k']
        for r in results:
            r['is_recommended'] = (r['k'] == best_k)
        
        execution_time = time.time() - start_time
        
        return {
            'results': results,
            'recommended_k': best_k,
            'execution_time': round(execution_time, 2)
        }

    def _generate_cluster_distribution(
        self,
        X: pd.DataFrame,
        labels: np.ndarray,
        n_clusters: int,
        centers: Optional[np.ndarray] = None
    ) -> List[Dict[str, Any]]:
        """
        生成聚类分布信息
        
        Args:
            X: 特征数据
            labels: 聚类标签
            n_clusters: 聚类数量
            centers: 聚类中心（可选）
            
        Returns:
            聚类分布列表
        """
        distribution = []
        total_samples = len(labels)
        overall_center = X.mean() if len(X) else pd.Series(dtype=float)
        
        # 获取唯一的聚类标签
        unique_labels = sorted(set(labels))
        
        for label in unique_labels:
            if label == -1:  # DBSCAN的噪声点
                cluster_name = "噪声点"
            else:
                cluster_name = f"聚类 {label}"
            
            mask = labels == label
            size = mask.sum()
            percentage = (size / total_samples * 100) if total_samples > 0 else 0
            
            # 计算聚类中心（均值），并将 numpy 标量转换为安全的 Python float
            cluster_data = X[mask]
            center_series = cluster_data.mean()
            center = {col: safe_float(val) for col, val in center_series.items()}
            
            # 计算特征统计
            feature_stats = {}
            for col in X.columns:
                feature_stats[col] = {
                    'mean': safe_float(cluster_data[col].mean()),
                    'std': safe_float(cluster_data[col].std()),
                    'min': safe_float(cluster_data[col].min()),
                    'max': safe_float(cluster_data[col].max())
                }
            
            top_features = self._extract_top_feature_differences(center, overall_center, feature_stats)
            summary = self._build_cluster_summary(label, top_features)

            distribution.append({
                'cluster_id': int(label),
                'cluster_name': cluster_name,
                'size': int(size),
                'percentage': round(percentage, 2),
                'center': center,
                'feature_stats': feature_stats,
                'top_features': top_features,
                'summary': summary,
            })
        
        return distribution

    def _extract_top_feature_differences(
        self,
        cluster_center: Dict[str, float],
        overall_center: pd.Series,
        feature_stats: Dict[str, Dict[str, float]],
        top_n: int = 3,
    ) -> List[Dict[str, Any]]:
        diffs = []
        for feature, mean_val in cluster_center.items():
            if overall_center is None or feature not in overall_center:
                continue
            delta = mean_val - float(overall_center[feature])
            diffs.append(
                {
                    'feature': feature,
                    'mean': mean_val,
                    'delta': delta,
                    'std': feature_stats.get(feature, {}).get('std')
                }
            )

        diffs.sort(key=lambda item: abs(item['delta'] or 0), reverse=True)
        return diffs[:top_n]

    def _build_cluster_summary(self, cluster_id: int, top_features: List[Dict[str, Any]]) -> str:
        if not top_features:
            return f"聚类 {cluster_id}: 未找到显著特征差异"

        parts = []
        for feat in top_features:
            direction = '高于' if (feat['delta'] or 0) >= 0 else '低于'
            parts.append(f"{feat['feature']} {direction}整体 {abs(feat['delta']):.2f}")

        joined = '，'.join(parts)
        return f"聚类 {cluster_id}: {joined}"

    def _attach_time_trend_metadata(
        self,
        result: Dict[str, Any],
        df: pd.DataFrame,
        labels: np.ndarray,
        region_names: List[str],
    ) -> None:
        time_trends, comments = self._generate_region_time_trends(df, labels, region_names)
        result['time_trends'] = time_trends
        result['cluster_comments'] = comments

    def _generate_region_time_trends(
        self,
        df: pd.DataFrame,
        labels: np.ndarray,
        region_names: List[str],
        freq: str = '30min',
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        timestamp_col = self._detect_timestamp_column(df)
        if not timestamp_col or len(labels) != len(region_names):
            return [], []

        timestamps = pd.to_datetime(df[timestamp_col], errors='coerce')
        region_series = df[region_names].apply(pd.to_numeric, errors='coerce')

        cluster_map = {region: int(label) for region, label in zip(region_names, labels)}
        unique_clusters = sorted(set(cluster_map.values()))

        time_trends: List[Dict[str, Any]] = []
        comments: List[str] = []

        for cid in unique_clusters:
            members = [region for region, lbl in cluster_map.items() if lbl == cid]
            valid_members = [m for m in members if m in region_series.columns]
            if not valid_members:
                continue

            cluster_values = region_series[valid_members].mean(axis=1)
            trend_df = pd.DataFrame({'timestamp': timestamps, 'value': cluster_values})
            trend_df = trend_df.dropna(subset=['timestamp', 'value']).sort_values('timestamp')
            if trend_df.empty:
                continue

            trend_df = trend_df.set_index('timestamp')
            resampled = trend_df['value'].resample(freq).mean().dropna()
            points = [
                {
                    'timestamp': ts.isoformat(),
                    'value': float(round(val, 6)),
                }
                for ts, val in resampled.items()
            ]

            time_trends.append(
                {
                    'cluster_id': int(cid),
                    'points': points,
                }
            )

            peak_time = resampled.idxmax() if not resampled.empty else None
            peak_value = float(resampled.max()) if not resampled.empty else None
            member_preview = ', '.join(valid_members[:5])
            if len(valid_members) > 5:
                member_preview += '…'

            if peak_time is not None and peak_value is not None:
                summary = (
                    f"聚类 {cid}: {len(valid_members)} 个地区（{member_preview}），"
                    f"峰值 {peak_value:.2f} 出现在 {peak_time.isoformat()}"
                )
            else:
                summary = f"聚类 {cid}: {len(valid_members)} 个地区（{member_preview}）"

            comments.append(summary)

        return time_trends, comments

    def _detect_timestamp_column(self, df: pd.DataFrame) -> Optional[str]:
        datetime_cols = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]
        if datetime_cols:
            return datetime_cols[0]

        for col in df.columns:
            parsed = pd.to_datetime(df[col], errors='coerce')
            if parsed.notna().sum() >= max(3, len(df) * 0.5):
                df[col] = parsed
                return col

        # 默认把第一列当作时间戳列处理
        if len(df.columns) > 0:
            first_col = df.columns[0]
            df[first_col] = pd.to_datetime(df[first_col], errors='coerce')
            return first_col

        return None


# 创建全局服务实例
cluster_service = ClusterService()
