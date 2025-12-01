"""
预测分析服务模块

该模块提供了多种时间序列预测模型的实现，包括：
- STL分解 + 多项式回归
- SARIMAX季节ARIMA
- XGBoost梯度提升树
- LightGBM梯度提升树
- CatBoost梯度提升树
- XGBoost + 随机森林残差
- LSTM深度时序网络
- GRU深度时序网络
- CNN一维卷积网络
- TCN时序卷积网络

支持单地区单模型预测和多地区多模型批量预测，适用于无线业务场景的数据分析和预测。
"""
import logging
from datetime import datetime
import traceback
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor



# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PredictionService:
    """预测分析服务类"""

    def __init__(self):
        """初始化预测服务"""
        self.upload_dir = Path(__file__).resolve().parents[2] / "uploads"
        logger.info("预测分析服务初始化完成，上传目录: %s", self.upload_dir)

    def _load_timeseries(
        self,
        filename: str,
        area_column: str,
        timestamp_index: int = 0,
    ) -> pd.Series:
        """从上传目录加载指定文件和地区列的时间序列数据"""
        file_path = self.upload_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        df = pd.read_csv(file_path)
        if df.shape[1] < 2:
            raise ValueError("CSV 至少需要一列时间戳和一列地区数据")

        # 第一列作为时间索引
        time_col = df.columns[timestamp_index]
        df[time_col] = pd.to_datetime(df[time_col])
        df = df.set_index(time_col).sort_index()

        if area_column not in df.columns:
            raise ValueError(f"地区列不存在: {area_column}")

        series = df[area_column].astype(float)
        series = series.replace([np.inf, -np.inf], np.nan).dropna()

        if series.empty:
            raise ValueError("选择的时间序列为空")

        return series

    def _train_test_future_split(self, series: pd.Series) -> Dict[str, Any]:
        """按照前 3/4 训练、后 1/4 测试，并向后预测 1/8 长度所需的基础切分信息"""

        n = len(series)
        if n < 8:
            raise ValueError("时间序列长度过短，无法按 3/4 + 1/4 + 1/8 切分")

        train_end = int(n * 0.75)
        test_start = train_end
        test_end = n
        future_steps = max(1, n // 8)

        return {
            "train": series.iloc[:train_end],
            "test": series.iloc[test_start:test_end],
            "future_steps": future_steps,
        }

    def sarima_timeseries_prediction(
        self,
        filename: str,
        area_column: str,
        order: tuple = (1, 1, 1),
        stl_reg_params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """基于 STL 分解 + 线性回归的时间序列预测：3/4 训练，1/4 测试，并向后预测 1/8"""

        series = self._load_timeseries(filename=filename, area_column=area_column)

        # 可选：仅使用最近一段窗口的数据进行建模，以适应结构变化较大的序列
        # 窗口长度按照天数 * 周期粗略估算；当 days_window<=0 或未提供时，使用全部数据
        params = stl_reg_params or {}
        base_period = int(params.get("period", 140))
        days_window = int(params.get("days_window", 0))  # 0 表示不启用窗口
        if days_window > 0:
            max_points = days_window * base_period
            if len(series) > max_points:
                series = series.iloc[-max_points:]

        # 使用处理后的时间序列进行 3/4 训练 + 1/4 测试 + 1/8 未来 切分
        split = self._train_test_future_split(series)
        train, test, future_steps = split["train"], split["test"], split["future_steps"]

        logger.info(
            "开始 STL+线性回归 预测，文件=%s, 地区=%s, 训练样本=%s, 测试样本=%s, 未来步长=%s",
            filename,
            area_column,
            len(train),
            len(test),
            future_steps,
        )

        # 1. 在训练集上做 STL 分解
        # 默认：时间粒度为 10 分钟，日周期为 140；允许通过 stl_reg_params 调整
        period = int(params.get("period", base_period))
        # 允许 1~3 阶多项式趋势，超过范围的值会被截断
        degree = int(params.get("degree", 2))
        if degree < 1:
            degree = 1
        elif degree > 3:
            degree = 3
        robust = bool(params.get("robust", True))

        stl = STL(train, period=period, robust=robust)
        stl_res = stl.fit()
        trend_train = stl_res.trend
        seasonal_train = stl_res.seasonal

        # 2. 用线性/多项式回归拟合趋势（以时间步作为自变量）
        n_train = len(trend_train)
        n_test = len(test)
        n_future = future_steps

        t_train = np.arange(n_train).reshape(-1, 1).astype(float)

        # 根据 degree 构造 1~3 阶多项式特征：t, t^2, t^3
        poly_feats = [t_train]
        if degree >= 2:
            poly_feats.append(t_train ** 2)
        if degree >= 3:
            poly_feats.append(t_train ** 3)
        X_train = np.hstack(poly_feats)

        lr = LinearRegression()
        lr.fit(X_train, trend_train.values)

        # 在训练+测试+未来区间上预测趋势
        total_steps = n_train + n_test + n_future
        t_all = np.arange(total_steps).reshape(-1, 1).astype(float)
        poly_all = [t_all]
        if degree >= 2:
            poly_all.append(t_all ** 2)
        if degree >= 3:
            poly_all.append(t_all ** 3)
        X_all = np.hstack(poly_all)

        trend_all_pred = lr.predict(X_all)

        # 3. 将季节成分扩展到训练+测试+未来区间（循环复用一个 period）
        seasonal_pattern = seasonal_train.values[-period:]
        if len(seasonal_pattern) < period:
            # 若训练数据不足一个周期，则直接使用已有部分循环
            seasonal_pattern = seasonal_train.values

        seasonal_all = np.array([
            seasonal_pattern[i % len(seasonal_pattern)] for i in range(total_steps)
        ])

        # 4. 合成预测值：趋势预测 + 季节项
        y_all_pred = trend_all_pred + seasonal_all

        # 切分出测试区间预测和未来预测
        test_pred = y_all_pred[n_train:n_train + n_test]
        future_forecast = y_all_pred[n_train + n_test:]

        # 指标基于测试区间真实值 vs 预测值
        history_index = [ts.isoformat() for ts in series.index]
        train_index = [ts.isoformat() for ts in train.index]
        test_index = [ts.isoformat() for ts in test.index]

        if series.index.inferred_freq is not None:
            future_index = [
                ts.isoformat()
                for ts in pd.date_range(
                    series.index[-1],
                    periods=future_steps + 1,
                    freq=series.index.inferred_freq,
                )[1:]
            ]
        else:
            future_index = list(range(len(series), len(series) + future_steps))

        return {
            "area": area_column,
            "history_index": history_index,
            "history_values": series.tolist(),
            "train_index": train_index,
            "train_values": train.tolist(),
            "test_index": test_index,
            "test_values": test.tolist(),
            "test_pred_values": test_pred.tolist(),
            "future_index": future_index,
            "future_forecast_values": future_forecast.tolist(),
            "metrics": {
                "mae": float(mean_absolute_error(test, test_pred)),
                "mse": float(mean_squared_error(test, test_pred)),
                "rmse": float(mean_squared_error(test, test_pred, squared=False)),
            },
        }

    def xgboost_timeseries_prediction(
        self,
        filename: str,
        area_column: str,
        xgb_params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """基于 XGBoost 回归的时间序列预测：3/4 训练，1/4 测试，并向后预测 1/8。

        与纯滞后特征相比，增加趋势 + 正弦余弦季节特征，提升对周期的拟合能力。
        """

        series = self._load_timeseries(filename=filename, area_column=area_column)

        params = xgb_params or {}
        seasonal_period = int(params.get("seasonal_period", 140))
        days_window = int(params.get("days_window", 0))
        seasonal_period = max(seasonal_period, 1)

        def _parse_bool(value: Any, default: bool) -> bool:
            if value is None:
                return default
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "y"}
            return bool(value)

        use_seasonal_features = _parse_bool(params.get("use_seasonal_features", True), True)
        seasonal_harmonics = max(int(params.get("seasonal_harmonics", 2)), 1)
        use_trend_features = _parse_bool(params.get("use_trend_features", True), True)
        trend_degree = max(int(params.get("trend_degree", 1)), 1)

        if days_window > 0:
            max_points = days_window * seasonal_period
            if len(series) > max_points:
                series = series.iloc[-max_points:]

        split = self._train_test_future_split(series)
        train_series, test_series, future_steps = (
            split["train"],
            split["test"],
            split["future_steps"],
        )

        logger.info(
            "开始 XGBoost 预测，文件=%s, 地区=%s, 训练样本=%s, 测试样本=%s, 未来步长=%s",
            filename,
            area_column,
            len(train_series),
            len(test_series),
            future_steps,
        )

        lag = int(params.get("lag", 10))
        if lag < 1:
            lag = 1
        if len(series) <= lag + 5:
            raise ValueError("时间序列长度不足以构造 XGBoost 滞后特征")

        values = series.values.astype(float)
        total_len = len(values)

        def build_stat_features(window: np.ndarray) -> np.ndarray:
            if window.size == 0:
                return np.array([], dtype=float)
            max_val = float(np.max(window))
            min_val = float(np.min(window))
            return np.array(
                [
                    float(np.mean(window)),
                    float(np.std(window)),
                    max_val,
                    min_val,
                    max_val - min_val,
                    float(window[-1] - window[0]),
                ],
                dtype=float,
            )

        def build_extra_features(time_pos: int) -> np.ndarray:
            feats: List[float] = []
            if use_trend_features:
                t_norm = time_pos / max(total_len, 1)
                feats.append(t_norm)
                if trend_degree >= 2:
                    feats.append(t_norm ** 2)
                if trend_degree >= 3:
                    feats.append(t_norm ** 3)
            if use_seasonal_features and seasonal_period > 0:
                for k in range(1, seasonal_harmonics + 1):
                    angle = 2 * np.pi * k * time_pos / seasonal_period
                    feats.append(np.sin(angle))
                    feats.append(np.cos(angle))
            return np.asarray(feats, dtype=float) if feats else np.array([], dtype=float)

        X_all, y_all, index_all = [], [], []
        for t in range(lag, len(values)):
            lag_features = values[t - lag : t]
            stat_feats = build_stat_features(lag_features)
            extra = build_extra_features(t)
            feature_parts = [lag_features]
            if stat_feats.size:
                feature_parts.append(stat_feats)
            if extra.size:
                feature_parts.append(extra)
            features = np.concatenate(feature_parts)
            X_all.append(features)
            y_all.append(values[t])
            index_all.append(series.index[t])

        X_all = np.asarray(X_all)
        y_all = np.asarray(y_all)
        index_all = pd.DatetimeIndex(index_all)

        train_end_ts = train_series.index[-1]
        test_end_ts = test_series.index[-1]
        train_end_pos = index_all.get_indexer([train_end_ts], method="pad")[0]
        test_end_pos = index_all.get_indexer([test_end_ts], method="pad")[0]

        X_train = X_all[: train_end_pos + 1]
        y_train = y_all[: train_end_pos + 1]
        X_test = X_all[train_end_pos + 1 : test_end_pos + 1]
        y_test = y_all[train_end_pos + 1 : test_end_pos + 1]

        model = XGBRegressor(
            n_estimators=int(params.get("n_estimators", 200)),
            max_depth=int(params.get("max_depth", 4)),
            learning_rate=float(params.get("learning_rate", 0.05)),
            subsample=float(params.get("subsample", 0.8)),
            colsample_bytree=float(params.get("colsample_bytree", 0.8)),
            objective="reg:squarederror",
            n_jobs=4,
            verbosity=0,
        )
        model.fit(X_train, y_train)

        test_pred = model.predict(X_test) if len(X_test) > 0 else np.array([])

        future_forecast = []
        history_for_future = values.copy()
        for step in range(future_steps):
            if len(history_for_future) < lag:
                break
            lag_input = history_for_future[-lag:]
            stat_feats = build_stat_features(lag_input)
            extra = build_extra_features(total_len + step)
            feature_parts = [lag_input]
            if stat_feats.size:
                feature_parts.append(stat_feats)
            if extra.size:
                feature_parts.append(extra)
            x_input = np.concatenate(feature_parts)
            y_hat = float(model.predict(x_input.reshape(1, -1))[0])
            future_forecast.append(y_hat)
            history_for_future = np.append(history_for_future, y_hat)

        history_index = [ts.isoformat() for ts in series.index]
        train_index = [ts.isoformat() for ts in train_series.index]
        test_index = [ts.isoformat() for ts in test_series.index]

        if series.index.inferred_freq is not None:
            future_index = [
                ts.isoformat()
                for ts in pd.date_range(
                    series.index[-1],
                    periods=future_steps + 1,
                    freq=series.index.inferred_freq,
                )[1:]
            ]
        else:
            future_index = list(range(len(series), len(series) + future_steps))

        metrics: Dict[str, Any] = {}
        if len(y_test) > 0 and len(test_pred) == len(y_test):
            metrics = {
                "mae": float(mean_absolute_error(y_test, test_pred)),
                "mse": float(mean_squared_error(y_test, test_pred)),
                "rmse": float(mean_squared_error(y_test, test_pred, squared=False)),
            }

        return {
            "area": area_column,
            "history_index": history_index,
            "history_values": series.tolist(),
            "train_index": train_index,
            "train_values": train_series.tolist(),
            "test_index": test_index,
            "test_values": test_series.tolist(),
            "test_pred_values": test_pred.tolist(),
            "future_index": future_index,
            "future_forecast_values": future_forecast,
            "metrics": metrics,
        }

    def lightgbm_timeseries_prediction(
        self,
        filename: str,
        area_column: str,
        lgbm_params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """基于 LightGBM 回归的时间序列预测：3/4 训练，1/4 测试，并向后预测 1/8。

        特征工程与 XGBoost 模型保持一致，便于对比不同树模型效果。
        """

        series = self._load_timeseries(filename=filename, area_column=area_column)

        params = lgbm_params or {}
        seasonal_period = int(params.get("seasonal_period", 140))
        days_window = int(params.get("days_window", 0))
        seasonal_period = max(seasonal_period, 1)

        def _parse_bool(value: Any, default: bool) -> bool:
            if value is None:
                return default
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "y"}
            return bool(value)

        use_seasonal_features = _parse_bool(params.get("use_seasonal_features", True), True)
        seasonal_harmonics = max(int(params.get("seasonal_harmonics", 2)), 1)
        use_trend_features = _parse_bool(params.get("use_trend_features", True), True)
        trend_degree = max(int(params.get("trend_degree", 1)), 1)

        if days_window > 0:
            max_points = days_window * seasonal_period
            if len(series) > max_points:
                series = series.iloc[-max_points:]

        split = self._train_test_future_split(series)
        train_series, test_series, future_steps = (
            split["train"],
            split["test"],
            split["future_steps"],
        )

        logger.info(
            "开始 LightGBM 预测，文件=%s, 地区=%s, 训练样本=%s, 测试样本=%s, 未来步长=%s",
            filename,
            area_column,
            len(train_series),
            len(test_series),
            future_steps,
        )

        lag = int(params.get("lag", 10))
        if lag < 1:
            lag = 1
        if len(series) <= lag + 5:
            raise ValueError("时间序列长度不足以构造 LightGBM 滞后特征")

        values = series.values.astype(float)
        total_len = len(values)

        def build_stat_features(window: np.ndarray) -> np.ndarray:
            if window.size == 0:
                return np.array([], dtype=float)
            max_val = float(np.max(window))
            min_val = float(np.min(window))
            return np.array(
                [
                    float(np.mean(window)),
                    float(np.std(window)),
                    max_val,
                    min_val,
                    max_val - min_val,
                    float(window[-1] - window[0]),
                ],
                dtype=float,
            )

        def build_extra_features(time_pos: int) -> np.ndarray:
            feats: List[float] = []
            if use_trend_features:
                t_norm = time_pos / max(total_len, 1)
                feats.append(t_norm)
                if trend_degree >= 2:
                    feats.append(t_norm ** 2)
                if trend_degree >= 3:
                    feats.append(t_norm ** 3)
            if use_seasonal_features and seasonal_period > 0:
                for k in range(1, seasonal_harmonics + 1):
                    angle = 2 * np.pi * k * time_pos / seasonal_period
                    feats.append(np.sin(angle))
                    feats.append(np.cos(angle))
            return np.asarray(feats, dtype=float) if feats else np.array([], dtype=float)

        X_all, y_all, index_all = [], [], []
        for t in range(lag, len(values)):
            lag_features = values[t - lag : t]
            stat_feats = build_stat_features(lag_features)
            extra = build_extra_features(t)
            feature_parts = [lag_features]
            if stat_feats.size:
                feature_parts.append(stat_feats)
            if extra.size:
                feature_parts.append(extra)
            features = np.concatenate(feature_parts)
            X_all.append(features)
            y_all.append(values[t])
            index_all.append(series.index[t])

        X_all = np.asarray(X_all)
        y_all = np.asarray(y_all)
        index_all = pd.DatetimeIndex(index_all)

        train_end_ts = train_series.index[-1]
        test_end_ts = test_series.index[-1]
        train_end_pos = index_all.get_indexer([train_end_ts], method="pad")[0]
        test_end_pos = index_all.get_indexer([test_end_ts], method="pad")[0]

        X_train = X_all[: train_end_pos + 1]
        y_train = y_all[: train_end_pos + 1]
        X_test = X_all[train_end_pos + 1 : test_end_pos + 1]
        y_test = y_all[train_end_pos + 1 : test_end_pos + 1]

        model = LGBMRegressor(
            n_estimators=int(params.get("n_estimators", 400)),
            max_depth=int(params.get("max_depth", -1)),
            learning_rate=float(params.get("learning_rate", 0.05)),
            subsample=float(params.get("subsample", 0.8)),
            colsample_bytree=float(params.get("colsample_bytree", 0.8)),
            objective="regression",
            n_jobs=4,
        )
        model.fit(X_train, y_train)

        test_pred = model.predict(X_test) if len(X_test) > 0 else np.array([])

        future_forecast = []
        history_for_future = values.copy()
        for step in range(future_steps):
            if len(history_for_future) < lag:
                break
            lag_input = history_for_future[-lag:]
            stat_feats = build_stat_features(lag_input)
            extra = build_extra_features(total_len + step)
            feature_parts = [lag_input]
            if stat_feats.size:
                feature_parts.append(stat_feats)
            if extra.size:
                feature_parts.append(extra)
            x_input = np.concatenate(feature_parts)
            y_hat = float(model.predict(x_input.reshape(1, -1))[0])
            future_forecast.append(y_hat)
            history_for_future = np.append(history_for_future, y_hat)

        history_index = [ts.isoformat() for ts in series.index]
        train_index = [ts.isoformat() for ts in train_series.index]
        test_index = [ts.isoformat() for ts in test_series.index]

        if series.index.inferred_freq is not None:
            future_index = [
                ts.isoformat()
                for ts in pd.date_range(
                    series.index[-1],
                    periods=future_steps + 1,
                    freq=series.index.inferred_freq,
                )[1:]
            ]
        else:
            future_index = list(range(len(series), len(series) + future_steps))

        metrics: Dict[str, Any] = {}
        if len(y_test) > 0 and len(test_pred) == len(y_test):
            metrics = {
                "mae": float(mean_absolute_error(y_test, test_pred)),
                "mse": float(mean_squared_error(y_test, test_pred)),
                "rmse": float(mean_squared_error(y_test, test_pred, squared=False)),
            }

        return {
            "area": area_column,
            "history_index": history_index,
            "history_values": series.tolist(),
            "train_index": train_index,
            "train_values": train_series.tolist(),
            "test_index": test_index,
            "test_values": test_series.tolist(),
            "test_pred_values": test_pred.tolist(),
            "future_index": future_index,
            "future_forecast_values": future_forecast,
            "metrics": metrics,
        }

    def catboost_timeseries_prediction(
        self,
        filename: str,
        area_column: str,
        cat_params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """基于 CatBoost 回归的时间序列预测：3/4 训练，1/4 测试，并向后预测 1/8。

        特征工程与 XGBoost 模型保持一致。
        """

        series = self._load_timeseries(filename=filename, area_column=area_column)

        params = cat_params or {}
        seasonal_period = int(params.get("seasonal_period", 140))
        days_window = int(params.get("days_window", 0))
        seasonal_period = max(seasonal_period, 1)

        def _parse_bool(value: Any, default: bool) -> bool:
            if value is None:
                return default
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "y"}
            return bool(value)

        use_seasonal_features = _parse_bool(params.get("use_seasonal_features", True), True)
        seasonal_harmonics = max(int(params.get("seasonal_harmonics", 2)), 1)
        use_trend_features = _parse_bool(params.get("use_trend_features", True), True)
        trend_degree = max(int(params.get("trend_degree", 1)), 1)

        if days_window > 0:
            max_points = days_window * seasonal_period
            if len(series) > max_points:
                series = series.iloc[-max_points:]

        split = self._train_test_future_split(series)
        train_series, test_series, future_steps = (
            split["train"],
            split["test"],
            split["future_steps"],
        )

        logger.info(
            "开始 CatBoost 预测，文件=%s, 地区=%s, 训练样本=%s, 测试样本=%s, 未来步长=%s",
            filename,
            area_column,
            len(train_series),
            len(test_series),
            future_steps,
        )

        lag = int(params.get("lag", 10))
        if lag < 1:
            lag = 1
        if len(series) <= lag + 5:
            raise ValueError("时间序列长度不足以构造 CatBoost 滞后特征")

        values = series.values.astype(float)
        total_len = len(values)

        def build_stat_features(window: np.ndarray) -> np.ndarray:
            if window.size == 0:
                return np.array([], dtype=float)
            max_val = float(np.max(window))
            min_val = float(np.min(window))
            return np.array(
                [
                    float(np.mean(window)),
                    float(np.std(window)),
                    max_val,
                    min_val,
                    max_val - min_val,
                    float(window[-1] - window[0]),
                ],
                dtype=float,
            )

        def build_extra_features(time_pos: int) -> np.ndarray:
            feats: List[float] = []
            if use_trend_features:
                t_norm = time_pos / max(total_len, 1)
                feats.append(t_norm)
                if trend_degree >= 2:
                    feats.append(t_norm ** 2)
                if trend_degree >= 3:
                    feats.append(t_norm ** 3)
            if use_seasonal_features and seasonal_period > 0:
                for k in range(1, seasonal_harmonics + 1):
                    angle = 2 * np.pi * k * time_pos / seasonal_period
                    feats.append(np.sin(angle))
                    feats.append(np.cos(angle))
            return np.asarray(feats, dtype=float) if feats else np.array([], dtype=float)

        X_all, y_all, index_all = [], [], []
        for t in range(lag, len(values)):
            lag_features = values[t - lag : t]
            stat_feats = build_stat_features(lag_features)
            extra = build_extra_features(t)
            feature_parts = [lag_features]
            if stat_feats.size:
                feature_parts.append(stat_feats)
            if extra.size:
                feature_parts.append(extra)
            features = np.concatenate(feature_parts)
            X_all.append(features)
            y_all.append(values[t])
            index_all.append(series.index[t])

        X_all = np.asarray(X_all)
        y_all = np.asarray(y_all)
        index_all = pd.DatetimeIndex(index_all)

        train_end_ts = train_series.index[-1]
        test_end_ts = test_series.index[-1]
        train_end_pos = index_all.get_indexer([train_end_ts], method="pad")[0]
        test_end_pos = index_all.get_indexer([test_end_ts], method="pad")[0]

        X_train = X_all[: train_end_pos + 1]
        y_train = y_all[: train_end_pos + 1]
        X_test = X_all[train_end_pos + 1 : test_end_pos + 1]
        y_test = y_all[train_end_pos + 1 : test_end_pos + 1]

        model = CatBoostRegressor(
            iterations=int(params.get("iterations", 400)),
            depth=int(params.get("depth", 6)),
            learning_rate=float(params.get("learning_rate", 0.05)),
            loss_function="RMSE",
            verbose=False,
        )
        model.fit(X_train, y_train)

        test_pred = model.predict(X_test) if len(X_test) > 0 else np.array([])

        future_forecast = []
        history_for_future = values.copy()
        for step in range(future_steps):
            if len(history_for_future) < lag:
                break
            lag_input = history_for_future[-lag:]
            stat_feats = build_stat_features(lag_input)
            extra = build_extra_features(total_len + step)
            feature_parts = [lag_input]
            if stat_feats.size:
                feature_parts.append(stat_feats)
            if extra.size:
                feature_parts.append(extra)
            x_input = np.concatenate(feature_parts)
            y_hat = float(model.predict(x_input.reshape(1, -1))[0])
            future_forecast.append(y_hat)
            history_for_future = np.append(history_for_future, y_hat)

        history_index = [ts.isoformat() for ts in series.index]
        train_index = [ts.isoformat() for ts in train_series.index]
        test_index = [ts.isoformat() for ts in test_series.index]

        if series.index.inferred_freq is not None:
            future_index = [
                ts.isoformat()
                for ts in pd.date_range(
                    series.index[-1],
                    periods=future_steps + 1,
                    freq=series.index.inferred_freq,
                )[1:]
            ]
        else:
            future_index = list(range(len(series), len(series) + future_steps))

        metrics: Dict[str, Any] = {}
        if len(y_test) > 0 and len(test_pred) == len(y_test):
            metrics = {
                "mae": float(mean_absolute_error(y_test, test_pred)),
                "mse": float(mean_squared_error(y_test, test_pred)),
                "rmse": float(mean_squared_error(y_test, test_pred, squared=False)),
            }

        return {
            "area": area_column,
            "history_index": history_index,
            "history_values": series.tolist(),
            "train_index": train_index,
            "train_values": train_series.tolist(),
            "test_index": test_index,
            "test_values": test_series.tolist(),
            "test_pred_values": test_pred.tolist(),
            "future_index": future_index,
            "future_forecast_values": future_forecast,
            "metrics": metrics,
        }

    def xgb_rf_residual_timeseries_prediction(
        self,
        filename: str,
        area_column: str,
        hybrid_params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """XGBoost + 随机森林残差混合模型预测。

        - 第一步：使用 XGBoost 在窗口内拟合主序列（与 xgboost_timeseries_prediction 相同的特征和切分）。
        - 第二步：在同一特征上训练随机森林拟合残差 y - y_hat_xgb。
        - 第三步：在测试和未来区间上，将两者预测相加得到最终结果。
        """

        series = self._load_timeseries(filename=filename, area_column=area_column)

        params = hybrid_params or {}
        seasonal_period = int(params.get("seasonal_period", 140))
        days_window = int(params.get("days_window", 0))
        seasonal_period = max(seasonal_period, 1)

        def _parse_bool(value: Any, default: bool) -> bool:
            if value is None:
                return default
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "y"}
            return bool(value)

        use_seasonal_features = _parse_bool(params.get("use_seasonal_features", True), True)
        seasonal_harmonics = max(int(params.get("seasonal_harmonics", 2)), 1)
        use_trend_features = _parse_bool(params.get("use_trend_features", True), True)
        trend_degree = max(int(params.get("trend_degree", 1)), 1)

        if days_window > 0:
            max_points = days_window * seasonal_period
            if len(series) > max_points:
                series = series.iloc[-max_points:]

        # 3/4 训练 + 1/4 测试 + 1/8 未来
        split = self._train_test_future_split(series)
        train_series, test_series, future_steps = (
            split["train"],
            split["test"],
            split["future_steps"],
        )

        logger.info(
            "开始 XGBoost+RF 残差 预测，文件=%s, 地区=%s, 训练样本=%s, 测试样本=%s, 未来步长=%s",
            filename,
            area_column,
            len(train_series),
            len(test_series),
            future_steps,
        )

        lag = int(params.get("lag", 10))
        if lag < 1:
            lag = 1
        if len(series) <= lag + 5:
            raise ValueError("时间序列长度不足以构造混合模型滞后特征")

        values = series.values.astype(float)
        total_len = len(values)

        def build_stat_features(window: np.ndarray) -> np.ndarray:
            if window.size == 0:
                return np.array([], dtype=float)
            max_val = float(np.max(window))
            min_val = float(np.min(window))
            return np.array(
                [
                    float(np.mean(window)),
                    float(np.std(window)),
                    max_val,
                    min_val,
                    max_val - min_val,
                    float(window[-1] - window[0]),
                ],
                dtype=float,
            )

        def build_extra_features(time_pos: int) -> np.ndarray:
            feats: List[float] = []
            if use_trend_features:
                t_norm = time_pos / max(total_len, 1)
                feats.append(t_norm)
                if trend_degree >= 2:
                    feats.append(t_norm ** 2)
                if trend_degree >= 3:
                    feats.append(t_norm ** 3)
            if use_seasonal_features and seasonal_period > 0:
                for k in range(1, seasonal_harmonics + 1):
                    angle = 2 * np.pi * k * time_pos / seasonal_period
                    feats.append(np.sin(angle))
                    feats.append(np.cos(angle))
            return np.asarray(feats, dtype=float) if feats else np.array([], dtype=float)

        # 构造共享特征
        X_all, y_all, index_all = [], [], []
        for t in range(lag, len(values)):
            lag_features = values[t - lag : t]
            stat_feats = build_stat_features(lag_features)
            extra = build_extra_features(t)
            feature_parts = [lag_features]
            if stat_feats.size:
                feature_parts.append(stat_feats)
            if extra.size:
                feature_parts.append(extra)
            features = np.concatenate(feature_parts)
            X_all.append(features)
            y_all.append(values[t])
            index_all.append(series.index[t])

        X_all = np.asarray(X_all)
        y_all = np.asarray(y_all)
        index_all = pd.DatetimeIndex(index_all)

        # 按时间边界切分 train/test
        train_end_ts = train_series.index[-1]
        test_end_ts = test_series.index[-1]
        train_end_pos = index_all.get_indexer([train_end_ts], method="pad")[0]
        test_end_pos = index_all.get_indexer([test_end_ts], method="pad")[0]

        X_train = X_all[: train_end_pos + 1]
        y_train = y_all[: train_end_pos + 1]
        X_test = X_all[train_end_pos + 1 : test_end_pos + 1]
        y_test = y_all[train_end_pos + 1 : test_end_pos + 1]

        # 1) 训练 XGBoost 主模型
        xgb_model = XGBRegressor(
            n_estimators=int(params.get("n_estimators", 200)),
            max_depth=int(params.get("max_depth", 4)),
            learning_rate=float(params.get("learning_rate", 0.05)),
            subsample=float(params.get("subsample", 0.8)),
            colsample_bytree=float(params.get("colsample_bytree", 0.8)),
            objective="reg:squarederror",
            n_jobs=4,
            verbosity=0,
        )
        xgb_model.fit(X_train, y_train)

        base_all_pred = xgb_model.predict(X_all)
        base_train_pred = base_all_pred[: train_end_pos + 1]
        base_test_pred = base_all_pred[train_end_pos + 1 : test_end_pos + 1]

        # 2) 训练随机森林拟合残差
        residual_all = y_all - base_all_pred
        res_train = residual_all[: train_end_pos + 1]
        res_test = residual_all[train_end_pos + 1 : test_end_pos + 1]

        rf_model = RandomForestRegressor(
            n_estimators=int(params.get("rf_n_estimators", 200)),
            max_depth=int(params.get("rf_max_depth", 8)),
            min_samples_split=int(params.get("rf_min_samples_split", 2)),
            min_samples_leaf=int(params.get("rf_min_samples_leaf", 1)),
            max_features=params.get("rf_max_features", "sqrt"),
            random_state=int(params.get("rf_random_state", 42)),
            bootstrap=bool(params.get("rf_bootstrap", True)),
        )
        rf_model.fit(X_train, res_train)

        rf_test_pred = rf_model.predict(X_test)

        # 残差权重：>1 表示更“激进”地使用 RF 残差
        rf_weight = float(params.get("rf_residual_weight", 1.2))

        # 组合得到最终测试区间预测
        final_test_pred = base_test_pred + rf_weight * rf_test_pred

        # 3) 未来预测：XGBoost + RF 残差共同递归
        future_forecast: List[float] = []
        history_for_future = values.copy()
        for step in range(future_steps):
            if len(history_for_future) < lag:
                break
            lag_input = history_for_future[-lag:]
            stat_feats = build_stat_features(lag_input)
            extra = build_extra_features(total_len + step)
            feature_parts = [lag_input]
            if stat_feats.size:
                feature_parts.append(stat_feats)
            if extra.size:
                feature_parts.append(extra)
            x_input = np.concatenate(feature_parts).reshape(1, -1)

            base_hat = float(xgb_model.predict(x_input)[0])
            res_hat = float(rf_model.predict(x_input)[0])
            y_hat = base_hat + rf_weight * res_hat
            future_forecast.append(y_hat)
            history_for_future = np.append(history_for_future, y_hat)

        # 索引与其它模型保持一致
        history_index = [ts.isoformat() for ts in series.index]
        train_index = [ts.isoformat() for ts in train_series.index]
        test_index = [ts.isoformat() for ts in test_series.index]

        if series.index.inferred_freq is not None:
            future_index = [
                ts.isoformat()
                for ts in pd.date_range(
                    series.index[-1],
                    periods=future_steps + 1,
                    freq=series.index.inferred_freq,
                )[1:]
            ]
        else:
            future_index = list(range(len(series), len(series) + future_steps))

        metrics: Dict[str, Any] = {}
        if len(y_test) > 0 and len(final_test_pred) == len(y_test):
            metrics = {
                "mae": float(mean_absolute_error(y_test, final_test_pred)),
                "mse": float(mean_squared_error(y_test, final_test_pred)),
                "rmse": float(mean_squared_error(y_test, final_test_pred, squared=False)),
            }

        return {
            "area": area_column,
            "history_index": history_index,
            "history_values": series.tolist(),
            "train_index": train_index,
            "train_values": train_series.tolist(),
            "test_index": test_index,
            "test_values": test_series.tolist(),
            "test_pred_values": final_test_pred.tolist(),
            "future_index": future_index,
            "future_forecast_values": future_forecast,
            "metrics": metrics,
        }

    def sarimax_timeseries_prediction(
        self,
        filename: str,
        area_column: str,
        sarima_params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """基于 SARIMAX 的季节 ARIMA 预测：3/4 训练，1/4 测试，并向后预测 1/8。

        与 sarima_timeseries_prediction 一致，增加了：
        - 使用 SARIMAX(order, seasonal_order) 直接在差分后序列上建模；
        - 支持 days_window：0 或缺省表示使用全部数据，>0 仅使用最近 N 天数据建模。
        """

        series = self._load_timeseries(filename=filename, area_column=area_column)

        params = sarima_params or {}
        # 从参数中解析季节周期和窗口长度
        seasonal_period = int(params.get("seasonal_period", 140))
        days_window = int(params.get("days_window", 0))  # 0 表示不启用窗口

        # 可选：仅使用最近一段窗口的数据进行建模
        if days_window > 0:
            max_points = days_window * seasonal_period
            if len(series) > max_points:
                series = series.iloc[-max_points:]

        # 3/4 训练 + 1/4 测试 + 1/8 未来
        split = self._train_test_future_split(series)
        train, test, future_steps = split["train"], split["test"], split["future_steps"]

        logger.info(
            "开始 SARIMAX 预测，文件=%s, 地区=%s, 训练样本=%s, 测试样本=%s, 未来步长=%s",
            filename,
            area_column,
            len(train),
            len(test),
            future_steps,
        )

        # 读取 SARIMA 参数
        # 1）优先使用前端拆开的 (p,d,q,P,D,Q) 字段；
        # 2）如缺失则回退到整体的 order / seasonal_order 或默认值。
        p = params.get("order_p")
        d = params.get("order_d")
        q = params.get("order_q")
        P = params.get("seasonal_P")
        D = params.get("seasonal_D")
        Q = params.get("seasonal_Q")

        if p is not None and d is not None and q is not None:
            order = (int(p), int(d), int(q))
        else:
            order = tuple(params.get("order", (1, 1, 1)))

        if P is not None and D is not None and Q is not None:
            seasonal_order = (int(P), int(D), int(Q), seasonal_period)
        else:
            so = params.get("seasonal_order", (0, 1, 1, seasonal_period))
            # 确保 seasonal_order 最后一个元素与 seasonal_period 一致
            if len(so) == 4:
                seasonal_order = (int(so[0]), int(so[1]), int(so[2]), int(seasonal_period))
            else:
                seasonal_order = (0, 1, 1, seasonal_period)

        # 在训练集上拟合 SARIMAX 模型（进一步限制迭代次数以加快拟合速度）
        model = SARIMAX(
            train,
            order=tuple(order),
            seasonal_order=tuple(seasonal_order),
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        # 使用较小的 maxiter 做“粗糙拟合”，在保证速度的前提下获得近似解
        model_fit = model.fit(maxiter=20, disp=False)

        n_test = len(test)
        n_future = future_steps

        # 预测测试 + 未来区间
        forecast_steps = n_test + n_future
        forecast_res = model_fit.get_forecast(steps=forecast_steps)
        forecast_mean = forecast_res.predicted_mean

        # 测试区间预测和未来预测
        test_pred = forecast_mean.iloc[:n_test]
        future_forecast = forecast_mean.iloc[n_test:]

        # 指标和索引构造与 STL 版本保持一致
        history_index = [ts.isoformat() for ts in series.index]
        train_index = [ts.isoformat() for ts in train.index]
        test_index = [ts.isoformat() for ts in test.index]

        if series.index.inferred_freq is not None:
            future_index = [
                ts.isoformat()
                for ts in pd.date_range(
                    series.index[-1],
                    periods=future_steps + 1,
                    freq=series.index.inferred_freq,
                )[1:]
            ]
        else:
            future_index = list(range(len(series), len(series) + future_steps))

        return {
            "area": area_column,
            "history_index": history_index,
            "history_values": series.tolist(),
            "train_index": train_index,
            "train_values": train.tolist(),
            "test_index": test_index,
            "test_values": test.tolist(),
            "test_pred_values": test_pred.tolist(),
            "future_index": future_index,
            "future_forecast_values": future_forecast.tolist(),
            "metrics": {
                "mae": float(mean_absolute_error(test, test_pred)),
                "mse": float(mean_squared_error(test, test_pred)),
                "rmse": float(mean_squared_error(test, test_pred, squared=False)),
            },
        }

    


    def batch_predict_by_areas(
        self,
        filename: str,
        area_columns: List[str],
        models: List[str],
        model_params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        
        logger.info("开始批量预测，文件=%s, 地区=%s, 模型=%s", filename, area_columns, models)
        
        # 加载数据 - 使用绝对路径
        file_path = self.upload_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        df = pd.read_csv(file_path)
        df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
        df.set_index(df.columns[0], inplace=True)
        
        results = {}
        model_params = model_params or {}
        
        for area in area_columns:
            if area not in df.columns:
                logger.warning("地区 %s 不存在于数据中，跳过", area)
                continue
                
            area_result: Dict[str, Any] = {}
            timestamps = None
            
            # 支持多种统计/机器学习/深度学习模型：
            # stl_reg（STL+回归）、sarima（SARIMAX）、xgboost（梯度提升树）、
            # xgb_rf_residual（XGBoost+随机森林残差）、lstm/gru/cnn/tcn（神经网络）
            for model in models:
                try:
                    logger.info("开始预测 %s 地区的 %s 模型", area, model)

                    if model == 'stl_reg':
                        params_for_model = model_params.get(model, {}) if isinstance(model_params, dict) else {}
                        result = self.sarima_timeseries_prediction(
                            filename=filename,
                            area_column=area,
                            stl_reg_params=params_for_model,
                        )
                        logger.info(f"STL+回归 预测成功，返回数据长度: {len(result.get('history_values', []))}")
                    elif model == 'sarima':
                        params_for_model = model_params.get(model, {}) if isinstance(model_params, dict) else {}
                        result = self.sarimax_timeseries_prediction(
                            filename=filename,
                            area_column=area,
                            sarima_params=params_for_model,
                        )
                        logger.info(f"SARIMAX 预测成功，返回数据长度: {len(result.get('history_values', []))}")
                    elif model == 'xgboost':
                        params_for_model = model_params.get(model, {}) if isinstance(model_params, dict) else {}
                        result = self.xgboost_timeseries_prediction(
                            filename=filename,
                            area_column=area,
                            xgb_params=params_for_model,
                        )
                        logger.info(f"XGBoost 预测成功，返回数据长度: {len(result.get('history_values', []))}")
                    elif model == 'lightgbm':
                        params_for_model = model_params.get(model, {}) if isinstance(model_params, dict) else {}
                        result = self.lightgbm_timeseries_prediction(
                            filename=filename,
                            area_column=area,
                            lgbm_params=params_for_model,
                        )
                        logger.info(f"LightGBM 预测成功，返回数据长度: {len(result.get('history_values', []))}")
                    elif model == 'catboost':
                        params_for_model = model_params.get(model, {}) if isinstance(model_params, dict) else {}
                        result = self.catboost_timeseries_prediction(
                            filename=filename,
                            area_column=area,
                            cat_params=params_for_model,
                        )
                        logger.info(f"CatBoost 预测成功，返回数据长度: {len(result.get('history_values', []))}")
                    elif model == 'xgb_rf_residual':
                        params_for_model = model_params.get(model, {}) if isinstance(model_params, dict) else {}
                        result = self.xgb_rf_residual_timeseries_prediction(
                            filename=filename,
                            area_column=area,
                            hybrid_params=params_for_model,
                        )
                        logger.info(f"XGBoost+RF 残差 预测成功，返回数据长度: {len(result.get('history_values', []))}")
                    elif model == 'lstm':
                        params_for_model = model_params.get(model, {}) if isinstance(model_params, dict) else {}
                        result = self.lstm_timeseries_prediction(
                            filename=filename,
                            area_column=area,
                            lstm_params=params_for_model,
                        )
                        logger.info(f"LSTM 预测成功，返回数据长度: {len(result.get('history_values', []))}")
                    elif model == 'gru':
                        params_for_model = model_params.get(model, {}) if isinstance(model_params, dict) else {}
                        result = self.gru_timeseries_prediction(
                            filename=filename,
                            area_column=area,
                            gru_params=params_for_model,
                        )
                        logger.info(f"GRU 预测成功，返回数据长度: {len(result.get('history_values', []))}")
                    elif model == 'cnn':
                        params_for_model = model_params.get(model, {}) if isinstance(model_params, dict) else {}
                        result = self.cnn_timeseries_prediction(
                            filename=filename,
                            area_column=area,
                            cnn_params=params_for_model,
                        )
                        logger.info(f"CNN 预测成功，返回数据长度: {len(result.get('history_values', []))}")
                    elif model == 'tcn':
                        params_for_model = model_params.get(model, {}) if isinstance(model_params, dict) else {}
                        result = self.tcn_timeseries_prediction(
                            filename=filename,
                            area_column=area,
                            tcn_params=params_for_model,
                        )
                        logger.info(f"TCN 预测成功，返回数据长度: {len(result.get('history_values', []))}")
                    else:
                        logger.warning(f"模型 {model} 暂未实现，跳过")
                        area_result[model] = []
                        continue
                    
                    # 模型内部使用的是可能被窗口截断后的 history_values
                    history_values = result.get("history_values", [])
                    train_values = result.get("train_values", [])
                    test_values = result.get("test_values", [])
                    test_pred_values = result.get("test_pred_values", [])
                    future_values = result.get("future_forecast_values", [])
                    history_index = result.get("history_index", [])

                    # 使用完整 df 构造全历史真实值和时间索引
                    full_series = df[area].astype(float).replace([np.inf, -np.inf], np.nan).dropna()
                    full_index = full_series.index
                    full_len = len(full_series)
                    future_len = len(future_values)

                    # 窗口起点对应的时间戳（模型内部使用的 history_index[0]）
                    if history_index:
                        window_start_ts = pd.to_datetime(history_index[0])
                        if window_start_ts in full_index:
                            window_start_pos = full_index.get_loc(window_start_ts)
                        else:
                            # 若未能在完整索引中找到，退化为从末尾对齐
                            window_start_pos = max(0, full_len - len(history_values))
                    else:
                        window_start_pos = max(0, full_len - len(history_values))

                    train_len = len(train_values)
                    test_len = len(test_values)

                    # 对 LSTM / GRU / CNN / TCN 来说，模型内部的第一个目标点从 sequence_length 之后才开始，
                    # 单地区接口已经用 effective_start=sequence_length 做了对齐。
                    # 这里在批量预测中也补上同样的偏移，避免整体提前一个窗口。
                    seq_offset = 0
                    if model in ("lstm", "gru", "cnn", "tcn"):
                        try:
                            seq_len = int(params_for_model.get("sequence_length", 144) or 144)
                        except Exception:
                            seq_len = 144
                        seq_offset = max(seq_len, 0)

                    train_start_index = window_start_pos + seq_offset

                    # 全局训练/测试结束索引（相对于完整时间轴）
                    train_end_index = train_start_index + max(0, train_len - 1)
                    test_end_index = train_start_index + max(0, train_len + test_len - 1)

                    # 统一构造未来时间索引：基于完整时间轴的最后一个时间点
                    if full_index.inferred_freq is not None:
                        future_index = [
                            ts
                            for ts in pd.date_range(
                                full_index[-1],
                                periods=future_len + 1,
                                freq=full_index.inferred_freq,
                            )[1:]
                        ]
                    else:
                        future_index = list(range(full_len, full_len + future_len))

                    # 全量时间戳：完整历史索引 + 未来索引
                    all_indices = list(full_index) + list(future_index)

                    # 构造真实值：完整历史真实值 + 未来为空
                    actual_values = full_series.tolist()
                    if future_len > 0:
                        actual_values.extend([None] * future_len)

                    # 构造预测值：长度与 actual_values 一致，默认全为 None
                    total_len = full_len + future_len
                    pred_series = [None] * total_len

                    # 将测试区间预测对齐到完整时间轴上
                    if test_pred_values and test_len > 0:
                        # 统一对齐策略：所有模型的测试集预测都直接接在各自的训练开始位置之后。
                        # 对 LSTM，训练开始位置已经包含了 sequence_length 的偏移。
                        for i, v in enumerate(test_pred_values):
                            idx = train_start_index + train_len + i
                            if 0 <= idx < full_len:
                                pred_series[idx] = float(v)

                    # 将未来预测紧接在测试区间之后，避免实线与虚线之间出现较大时间断层
                    if future_values:
                        for i, v in enumerate(future_values):
                            idx = test_end_index + 1 + i
                            if 0 <= idx < total_len:
                                pred_series[idx] = float(v)

                    area_result["actual"] = actual_values
                    area_result[model] = pred_series

                    # 同时保留该模型的评估指标，便于前端展示准确性
                    metrics = result.get("metrics")
                    if metrics is not None:
                        area_result[f"{model}_metrics"] = metrics

                    # 保存时间戳和切分索引（只需要一次）
                    if timestamps is None:
                        timestamps = [ts.isoformat() if not isinstance(ts, (int, float)) else ts for ts in all_indices]
                        area_result["train_end_index"] = train_end_index
                        area_result["test_end_index"] = test_end_index
                        
                except Exception as e:
                    error_msg = "预测失败 %s - %s: %s" % (area, model, str(e))
                    logger.error(error_msg)
                    logger.error("错误详情: %s", type(e).__name__)
                    logger.error("完整错误堆栈: %s", traceback.format_exc())
                    area_result[model] = []
            
            # 添加时间戳
            if timestamps:
                area_result['timestamps'] = timestamps
            
            results[area] = area_result
        
        return {
            "filename": filename,
            "areas": results,
            "models": models,
            "timestamp": datetime.now().isoformat()
        }


    def lstm_timeseries_prediction(
        self,
        filename: str,
        area_column: str,
        lstm_params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """使用 PyTorch LSTM 进行时间序列预测（CPU/未来可自动切 GPU）。"""

        try:
            import torch
            import torch.nn as nn
            from torch.utils.data import DataLoader, TensorDataset
            from sklearn.preprocessing import MinMaxScaler
        except ImportError as exc:  # noqa: BLE001
            logger.error("LSTM 需要安装 torch 和 scikit-learn: pip install torch scikit-learn")
            raise ImportError("LSTM 需要安装 torch 和 scikit-learn") from exc

        # 默认参数，保持与前端和 batch_predict_by_areas 一致
        default_params: Dict[str, Any] = {
            "sequence_length": 144,
            "days_window": 7,
            "hidden_size": 64,
            "num_layers": 1,
            "dropout": 0.1,
            "learning_rate": 0.001,
            "epochs": 120,
            "batch_size": 32,
            "early_stopping_patience": 8,
            "bidirectional": False,
        }

        if lstm_params:
            default_params.update(lstm_params)

        sequence_length = int(default_params["sequence_length"])
        if sequence_length <= 0:
            sequence_length = 144

        # 1. 加载时间序列并应用窗口限制
        series = self._load_timeseries(filename, area_column)
        series = series.astype(float).replace([np.inf, -np.inf], np.nan).dropna()

        days_window = int(default_params.get("days_window", 0))
        if days_window > 0:
            max_points = days_window * 144
            if len(series) > max_points:
                series = series.iloc[-max_points:]

        if len(series) <= sequence_length + 10:
            raise ValueError("时间序列长度不足以构造 LSTM 训练样本，请提供更多数据")

        # 2. 归一化到 [-1, 1]
        scaler = MinMaxScaler(feature_range=(-1, 1))
        scaled_data = scaler.fit_transform(series.values.reshape(-1, 1)).flatten()

        # 3. 构造序列样本 (num_samples, sequence_length)
        X_all, y_all = self._create_sequences(scaled_data, sequence_length)
        if len(X_all) < 50:
            raise ValueError(f"数据量不足，需要至少50个序列，当前只有{len(X_all)}个")

        total_samples = len(X_all)
        train_size = int(total_samples * 0.75)
        test_size = total_samples - train_size
        if train_size <= 0 or test_size <= 0:
            raise ValueError("LSTM 训练/测试样本数不足，请检查时间序列长度")

        X_train_np = X_all[:train_size]
        X_test_np = X_all[train_size:]
        y_train_np = y_all[:train_size]
        y_test_np = y_all[train_size:]

        # 转为张量，形状 (batch, seq_len, 1)
        X_train = torch.FloatTensor(X_train_np).unsqueeze(-1)
        y_train = torch.FloatTensor(y_train_np).unsqueeze(-1)
        X_test = torch.FloatTensor(X_test_np).unsqueeze(-1)

        train_dataset = TensorDataset(X_train, y_train)
        train_loader = DataLoader(
            train_dataset,
            batch_size=int(default_params["batch_size"]),
            shuffle=True,
        )

        class LSTMModel(nn.Module):
            def __init__(
                self,
                input_size: int = 1,
                hidden_size: int = 64,
                num_layers: int = 2,
                dropout: float = 0.2,
                bidirectional: bool = False,
            ) -> None:
                super().__init__()
                self.hidden_size = hidden_size
                self.num_layers = num_layers
                self.bidirectional = bidirectional

                self.lstm = nn.LSTM(
                    input_size=input_size,
                    hidden_size=hidden_size,
                    num_layers=num_layers,
                    batch_first=True,
                    dropout=dropout if num_layers > 1 else 0.0,
                    bidirectional=bidirectional,
                )

                out_dim = hidden_size * 2 if bidirectional else hidden_size
                self.dropout = nn.Dropout(dropout)
                self.fc = nn.Linear(out_dim, 1)

            def forward(self, x: torch.Tensor) -> torch.Tensor:  # type: ignore[override]
                out, _ = self.lstm(x)
                if self.bidirectional:
                    # 取最后一个时间步的前向和后向输出
                    forward_last = out[:, -1, : self.hidden_size]
                    backward_last = out[:, 0, self.hidden_size :]
                    feat = torch.cat([forward_last, backward_last], dim=1)
                else:
                    feat = out[:, -1, :]
                feat = self.dropout(feat)
                return self.fc(feat)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("LSTM 使用设备: %s", device)

        model = LSTMModel(
            input_size=1,
            hidden_size=int(default_params["hidden_size"]),
            num_layers=int(default_params["num_layers"]),
            dropout=float(default_params["dropout"]),
            bidirectional=bool(default_params.get("bidirectional", False)),
        ).to(device)

        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=float(default_params["learning_rate"]))

        best_loss = float("inf")
        patience_counter = 0

        for epoch in range(int(default_params["epochs"])):
            model.train()
            total_loss = 0.0
            for batch_X, batch_y in train_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)

                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

                total_loss += float(loss.item())

            avg_loss = total_loss / max(len(train_loader), 1)
            if avg_loss < best_loss:
                best_loss = avg_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= int(default_params["early_stopping_patience"]):
                    logger.info("LSTM 早停于第 %d 轮, 最佳训练损失 %.6f", epoch + 1, best_loss)
                    break

        model.eval()
        with torch.no_grad():
            train_pred_t = model(X_train.to(device)).cpu().numpy()
            test_pred_t = model(X_test.to(device)).cpu().numpy()

        # 未来预测：使用递归方式基于最后一个窗口逐步预测
        with torch.no_grad():
            last_seq = torch.FloatTensor(
                scaled_data[-sequence_length:]
            ).view(1, sequence_length, 1).to(device)
            future_steps = max(1, sequence_length // 8)
            future_scaled: list[float] = []

            current_seq = last_seq.clone()
            for _ in range(future_steps):
                pred = model(current_seq)[:, 0].cpu().numpy()[0]
                future_scaled.append(float(pred))

                seq_np = current_seq.cpu().numpy()[0]
                seq_np = np.roll(seq_np, -1, axis=0)
                seq_np[-1, 0] = pred
                current_seq = torch.FloatTensor(seq_np).unsqueeze(0).to(device)

        # 反归一化
        test_pred = scaler.inverse_transform(test_pred_t).flatten()
        future_pred = scaler.inverse_transform(
            np.array(future_scaled).reshape(-1, 1)
        ).flatten()

        y_train_inv = scaler.inverse_transform(y_train_np.reshape(-1, 1)).flatten()
        y_test_inv = scaler.inverse_transform(y_test_np.reshape(-1, 1)).flatten()

        # 构造索引，考虑 sequence_length 偏移
        history_index = series.index.tolist()
        effective_start = sequence_length
        effective_end = sequence_length + train_size + test_size
        if effective_end > len(history_index):
            effective_end = len(history_index)

        train_index = history_index[effective_start : effective_start + train_size]
        test_index = history_index[
            effective_start + train_size : effective_start + train_size + test_size
        ]

        # 未来时间索引
        if len(history_index) > 0:
            last_time = pd.to_datetime(history_index[-1])
            freq = pd.infer_freq(history_index)
            if freq:
                future_index = pd.date_range(
                    start=last_time, periods=future_steps + 1, freq=freq
                )[1:].tolist()
            else:
                future_index = pd.date_range(
                    start=last_time, periods=future_steps + 1, freq="10min"
                )[1:].tolist()
        else:
            future_index = list(range(future_steps))

        return {
            "area": area_column,
            "history_index": history_index,
            "history_values": series.values.tolist(),
            "train_index": train_index,
            "train_values": y_train_inv.tolist(),
            "test_index": test_index,
            "test_values": y_test_inv.tolist(),
            "test_pred_values": test_pred.tolist(),
            "future_index": future_index,
            "future_forecast_values": future_pred.tolist(),
            "metrics": {
                "mae": float(mean_absolute_error(y_test_inv, test_pred)),
                "mse": float(mean_squared_error(y_test_inv, test_pred)),
                "rmse": float(
                    mean_squared_error(y_test_inv, test_pred, squared=False)
                ),
            },
        }

    def tcn_timeseries_prediction(
        self,
        filename: str,
        area_column: str,
        tcn_params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """使用 PyTorch TCN（时间卷积网络）进行时间序列预测，接口风格与 LSTM/CNN 保持一致。"""

        try:
            import torch
            import torch.nn as nn
            from torch.utils.data import DataLoader, TensorDataset
            from sklearn.preprocessing import MinMaxScaler
        except ImportError as exc:  # noqa: BLE001
            logger.error("TCN 需要安装 torch 和 scikit-learn: pip install torch scikit-learn")
            raise ImportError("TCN 需要安装 torch 和 scikit-learn") from exc

        # 默认参数，与 CNN 近似，便于对比
        default_params: Dict[str, Any] = {
            "sequence_length": 144,
            "days_window": 7,
            "num_filters": 64,
            "kernel_size": 5,
            "num_layers": 3,
            "hidden_size": 96,
            "dropout": 0.05,
            "learning_rate": 0.001,
            "epochs": 150,
            "batch_size": 32,
            "early_stopping_patience": 10,
        }

        if tcn_params:
            default_params.update(tcn_params)

        sequence_length = int(default_params["sequence_length"])
        if sequence_length <= 0:
            sequence_length = 144

        # 1. 加载时间序列并应用窗口限制
        series = self._load_timeseries(filename, area_column)
        series = series.astype(float).replace([np.inf, -np.inf], np.nan).dropna()

        days_window = int(default_params.get("days_window", 0))
        if days_window > 0:
            max_points = days_window * 144
            if len(series) > max_points:
                series = series.iloc[-max_points:]

        if len(series) <= sequence_length + 10:
            raise ValueError("时间序列长度不足以构造 TCN 训练样本，请提供更多数据")

        # 2. 归一化到 [-1, 1]
        scaler = MinMaxScaler(feature_range=(-1, 1))
        scaled_data = scaler.fit_transform(series.values.reshape(-1, 1)).flatten()

        # 3. 构造序列样本 (num_samples, sequence_length)
        X_all, y_all = self._create_sequences(scaled_data, sequence_length)
        if len(X_all) < 50:
            raise ValueError(f"数据量不足，需要至少50个序列，当前只有{len(X_all)}个")

        total_samples = len(X_all)
        train_size = int(total_samples * 0.75)
        test_size = total_samples - train_size
        if train_size <= 0 or test_size <= 0:
            raise ValueError("TCN 训练/测试样本数不足，请检查时间序列长度")

        X_train_np = X_all[:train_size]
        X_test_np = X_all[train_size:]
        y_train_np = y_all[:train_size]
        y_test_np = y_all[train_size:]

        # 转为张量，TCN/CNN 输入为 (batch, channels=1, seq_len)
        X_train = torch.FloatTensor(X_train_np).unsqueeze(1)
        y_train = torch.FloatTensor(y_train_np).unsqueeze(-1)
        X_test = torch.FloatTensor(X_test_np).unsqueeze(1)

        train_dataset = TensorDataset(X_train, y_train)
        train_loader = DataLoader(
            train_dataset,
            batch_size=int(default_params["batch_size"]),
            shuffle=True,
        )

        class TCN1DModel(nn.Module):
            def __init__(
                self,
                in_channels: int = 1,
                num_filters: int = 32,
                kernel_size: int = 5,
                num_layers: int = 3,
                hidden_size: int = 64,
                dropout: float = 0.1,
            ) -> None:
                super().__init__()

                layers: list[nn.Module] = []
                current_channels = in_channels
                # 使用指数膨胀的扩张卷积
                for i in range(num_layers):
                    dilation = 2 ** i
                    padding = (kernel_size - 1) * dilation
                    conv = nn.Conv1d(
                        in_channels=current_channels,
                        out_channels=num_filters,
                        kernel_size=kernel_size,
                        dilation=dilation,
                        padding=padding,
                    )
                    layers.append(conv)
                    layers.append(nn.ReLU())
                    layers.append(nn.Dropout(dropout))
                    current_channels = num_filters

                self.tcn = nn.Sequential(*layers)
                self.dropout = nn.Dropout(dropout)
                self.fc = nn.Linear(num_filters * sequence_length, hidden_size)
                self.out = nn.Linear(hidden_size, 1)

            def forward(self, x: torch.Tensor) -> torch.Tensor:  # type: ignore[override]
                # x: (batch, 1, seq_len)
                feat = self.tcn(x)
                # 去除因 padding 带来的前部多余时间步，仅保留与输入长度一致的最后 sequence_length 个
                if feat.size(-1) > sequence_length:
                    feat = feat[:, :, -sequence_length:]
                # 使用 reshape 以兼容非连续张量
                feat = feat.reshape(feat.size(0), -1)
                feat = self.dropout(feat)
                feat = torch.relu(self.fc(feat))
                return self.out(feat)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("TCN 使用设备: %s", device)

        model = TCN1DModel(
            in_channels=1,
            num_filters=int(default_params["num_filters"]),
            kernel_size=int(default_params["kernel_size"]),
            num_layers=int(default_params["num_layers"]),
            hidden_size=int(default_params["hidden_size"]),
            dropout=float(default_params["dropout"]),
        ).to(device)

        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=float(default_params["learning_rate"]))

        best_loss = float("inf")
        patience_counter = 0

        for epoch in range(int(default_params["epochs"])):
            model.train()
            total_loss = 0.0
            for batch_X, batch_y in train_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)

                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

                total_loss += float(loss.item())

            avg_loss = total_loss / max(len(train_loader), 1)
            if avg_loss < best_loss:
                best_loss = avg_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= int(default_params["early_stopping_patience"]):
                    logger.info("TCN 早停于第 %d 轮, 最佳训练损失 %.6f", epoch + 1, best_loss)
                    break

        model.eval()
        with torch.no_grad():
            train_pred_t = model(X_train.to(device)).cpu().numpy()
            test_pred_t = model(X_test.to(device)).cpu().numpy()

        # 未来预测：使用递归方式基于最后一个窗口逐步预测
        with torch.no_grad():
            last_seq = torch.FloatTensor(
                scaled_data[-sequence_length:]
            ).view(1, 1, sequence_length).to(device)
            future_steps = max(1, sequence_length // 8)
            future_scaled: list[float] = []

            current_seq = last_seq.clone()
            for _ in range(future_steps):
                pred = model(current_seq)[:, 0].cpu().numpy()[0]
                future_scaled.append(float(pred))

                seq_np = current_seq.cpu().numpy()
                seq_np = np.roll(seq_np, -1, axis=2)
                seq_np[0, 0, -1] = pred
                current_seq = torch.FloatTensor(seq_np).to(device)

        # 反归一化
        test_pred = scaler.inverse_transform(test_pred_t).flatten()
        future_pred = scaler.inverse_transform(
            np.array(future_scaled).reshape(-1, 1)
        ).flatten()

        y_train_inv = scaler.inverse_transform(y_train_np.reshape(-1, 1)).flatten()
        y_test_inv = scaler.inverse_transform(y_test_np.reshape(-1, 1)).flatten()

        # 构造索引，考虑 sequence_length 偏移
        history_index = series.index.tolist()
        effective_start = sequence_length
        effective_end = sequence_length + train_size + test_size
        if effective_end > len(history_index):
            effective_end = len(history_index)

        train_index = history_index[effective_start : effective_start + train_size]
        test_index = history_index[
            effective_start + train_size : effective_start + train_size + test_size
        ]

        # 未来时间索引
        if len(history_index) > 0:
            last_time = pd.to_datetime(history_index[-1])
            freq = pd.infer_freq(history_index)
            if freq:
                future_index = pd.date_range(
                    start=last_time, periods=future_steps + 1, freq=freq
                )[1:].tolist()
            else:
                future_index = pd.date_range(
                    start=last_time, periods=future_steps + 1, freq="10min"
                )[1:].tolist()
        else:
            future_index = list(range(future_steps))

        return {
            "area": area_column,
            "history_index": history_index,
            "history_values": series.values.tolist(),
            "train_index": train_index,
            "train_values": y_train_inv.tolist(),
            "test_index": test_index,
            "test_values": y_test_inv.tolist(),
            "test_pred_values": test_pred.tolist(),
            "future_index": future_index,
            "future_forecast_values": future_pred.tolist(),
            "metrics": {
                "mae": float(mean_absolute_error(y_test_inv, test_pred)),
                "mse": float(mean_squared_error(y_test_inv, test_pred)),
                "rmse": float(
                    mean_squared_error(y_test_inv, test_pred, squared=False)
                ),
            },
        }

    def gru_timeseries_prediction(
        self,
        filename: str,
        area_column: str,
        gru_params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """使用 PyTorch GRU 进行时间序列预测，接口风格与 LSTM 保持一致。"""

        try:
            import torch
            import torch.nn as nn
            from torch.utils.data import DataLoader, TensorDataset
            from sklearn.preprocessing import MinMaxScaler
        except ImportError as exc:  # noqa: BLE001
            logger.error("GRU 需要安装 torch 和 scikit-learn: pip install torch scikit-learn")
            raise ImportError("GRU 需要安装 torch 和 scikit-learn") from exc

        # 默认参数，与 LSTM 保持一致，便于对比
        default_params: Dict[str, Any] = {
            "sequence_length": 144,
            "days_window": 7,
            "hidden_size": 64,
            "num_layers": 1,
            "dropout": 0.1,
            "learning_rate": 0.001,
            "epochs": 120,
            "batch_size": 32,
            "early_stopping_patience": 8,
            "bidirectional": False,
        }

        if gru_params:
            default_params.update(gru_params)

        sequence_length = int(default_params["sequence_length"])
        if sequence_length <= 0:
            sequence_length = 144

        # 1. 加载时间序列并应用窗口限制
        series = self._load_timeseries(filename, area_column)
        series = series.astype(float).replace([np.inf, -np.inf], np.nan).dropna()

        days_window = int(default_params.get("days_window", 0))
        if days_window > 0:
            max_points = days_window * 144
            if len(series) > max_points:
                series = series.iloc[-max_points:]

        if len(series) <= sequence_length + 10:
            raise ValueError("时间序列长度不足以构造 GRU 训练样本，请提供更多数据")

        # 2. 归一化到 [-1, 1]
        scaler = MinMaxScaler(feature_range=(-1, 1))
        scaled_data = scaler.fit_transform(series.values.reshape(-1, 1)).flatten()

        # 3. 构造序列样本 (num_samples, sequence_length)
        X_all, y_all = self._create_sequences(scaled_data, sequence_length)
        if len(X_all) < 50:
            raise ValueError(f"数据量不足，需要至少50个序列，当前只有{len(X_all)}个")

        total_samples = len(X_all)
        train_size = int(total_samples * 0.75)
        test_size = total_samples - train_size
        if train_size <= 0 or test_size <= 0:
            raise ValueError("GRU 训练/测试样本数不足，请检查时间序列长度")

        X_train_np = X_all[:train_size]
        X_test_np = X_all[train_size:]
        y_train_np = y_all[:train_size]
        y_test_np = y_all[train_size:]

        # 转为张量，形状 (batch, seq_len, 1)
        X_train = torch.FloatTensor(X_train_np).unsqueeze(-1)
        y_train = torch.FloatTensor(y_train_np).unsqueeze(-1)
        X_test = torch.FloatTensor(X_test_np).unsqueeze(-1)

        train_dataset = TensorDataset(X_train, y_train)
        train_loader = DataLoader(
            train_dataset,
            batch_size=int(default_params["batch_size"]),
            shuffle=True,
        )

        class GRUModel(nn.Module):
            def __init__(
                self,
                input_size: int = 1,
                hidden_size: int = 64,
                num_layers: int = 2,
                dropout: float = 0.2,
                bidirectional: bool = False,
            ) -> None:
                super().__init__()
                self.hidden_size = hidden_size
                self.num_layers = num_layers
                self.bidirectional = bidirectional

                self.gru = nn.GRU(
                    input_size=input_size,
                    hidden_size=hidden_size,
                    num_layers=num_layers,
                    batch_first=True,
                    dropout=dropout if num_layers > 1 else 0.0,
                    bidirectional=bidirectional,
                )

                out_dim = hidden_size * 2 if bidirectional else hidden_size
                self.dropout = nn.Dropout(dropout)
                self.fc = nn.Linear(out_dim, 1)

            def forward(self, x: torch.Tensor) -> torch.Tensor:  # type: ignore[override]
                out, _ = self.gru(x)
                if self.bidirectional:
                    forward_last = out[:, -1, : self.hidden_size]
                    backward_last = out[:, 0, self.hidden_size :]
                    feat = torch.cat([forward_last, backward_last], dim=1)
                else:
                    feat = out[:, -1, :]
                feat = self.dropout(feat)
                return self.fc(feat)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("GRU 使用设备: %s", device)

        model = GRUModel(
            input_size=1,
            hidden_size=int(default_params["hidden_size"]),
            num_layers=int(default_params["num_layers"]),
            dropout=float(default_params["dropout"]),
            bidirectional=bool(default_params.get("bidirectional", False)),
        ).to(device)

        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=float(default_params["learning_rate"]))

        best_loss = float("inf")
        patience_counter = 0

        for epoch in range(int(default_params["epochs"])):
            model.train()
            total_loss = 0.0
            for batch_X, batch_y in train_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)

                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

                total_loss += float(loss.item())

            avg_loss = total_loss / max(len(train_loader), 1)
            if avg_loss < best_loss:
                best_loss = avg_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= int(default_params["early_stopping_patience"]):
                    logger.info("GRU 早停于第 %d 轮, 最佳训练损失 %.6f", epoch + 1, best_loss)
                    break

        model.eval()
        with torch.no_grad():
            train_pred_t = model(X_train.to(device)).cpu().numpy()
            test_pred_t = model(X_test.to(device)).cpu().numpy()

        # 未来预测：使用递归方式基于最后一个窗口逐步预测
        with torch.no_grad():
            last_seq = torch.FloatTensor(
                scaled_data[-sequence_length:]
            ).view(1, sequence_length, 1).to(device)
            future_steps = max(1, sequence_length // 8)
            future_scaled: list[float] = []

            current_seq = last_seq.clone()
            for _ in range(future_steps):
                pred = model(current_seq)[:, 0].cpu().numpy()[0]
                future_scaled.append(float(pred))

                seq_np = current_seq.cpu().numpy()[0]
                seq_np = np.roll(seq_np, -1, axis=0)
                seq_np[-1, 0] = pred
                current_seq = torch.FloatTensor(seq_np).unsqueeze(0).to(device)

        # 反归一化
        test_pred = scaler.inverse_transform(test_pred_t).flatten()
        future_pred = scaler.inverse_transform(
            np.array(future_scaled).reshape(-1, 1)
        ).flatten()

        y_train_inv = scaler.inverse_transform(y_train_np.reshape(-1, 1)).flatten()
        y_test_inv = scaler.inverse_transform(y_test_np.reshape(-1, 1)).flatten()

        # 构造索引，考虑 sequence_length 偏移
        history_index = series.index.tolist()
        effective_start = sequence_length
        effective_end = sequence_length + train_size + test_size
        if effective_end > len(history_index):
            effective_end = len(history_index)

        train_index = history_index[effective_start : effective_start + train_size]
        test_index = history_index[
            effective_start + train_size : effective_start + train_size + test_size
        ]

        # 未来时间索引
        if len(history_index) > 0:
            last_time = pd.to_datetime(history_index[-1])
            freq = pd.infer_freq(history_index)
            if freq:
                future_index = pd.date_range(
                    start=last_time, periods=future_steps + 1, freq=freq
                )[1:].tolist()
            else:
                future_index = pd.date_range(
                    start=last_time, periods=future_steps + 1, freq="10min"
                )[1:].tolist()
        else:
            future_index = list(range(future_steps))

        return {
            "area": area_column,
            "history_index": history_index,
            "history_values": series.values.tolist(),
            "train_index": train_index,
            "train_values": y_train_inv.tolist(),
            "test_index": test_index,
            "test_values": y_test_inv.tolist(),
            "test_pred_values": test_pred.tolist(),
            "future_index": future_index,
            "future_forecast_values": future_pred.tolist(),
            "metrics": {
                "mae": float(mean_absolute_error(y_test_inv, test_pred)),
                "mse": float(mean_squared_error(y_test_inv, test_pred)),
                "rmse": float(
                    mean_squared_error(y_test_inv, test_pred, squared=False)
                ),
            },
        }

    def cnn_timeseries_prediction(
        self,
        filename: str,
        area_column: str,
        cnn_params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """使用 PyTorch 1D CNN 进行时间序列预测，接口风格与 LSTM 保持一致。"""

        try:
            import torch
            import torch.nn as nn
            from torch.utils.data import DataLoader, TensorDataset
            from sklearn.preprocessing import MinMaxScaler
        except ImportError as exc:  # noqa: BLE001
            logger.error("CNN 需要安装 torch 和 scikit-learn: pip install torch scikit-learn")
            raise ImportError("CNN 需要安装 torch 和 scikit-learn") from exc

        # 默认参数，与前端保持一致
        default_params: Dict[str, Any] = {
            "sequence_length": 144,
            "days_window": 7,
            "num_filters": 96,
            "kernel_size": 5,
            "num_layers": 3,
            "hidden_size": 128,
            "dropout": 0.05,
            "learning_rate": 0.001,
            "epochs": 180,
            "batch_size": 32,
            "early_stopping_patience": 12,
        }

        if cnn_params:
            default_params.update(cnn_params)

        sequence_length = int(default_params["sequence_length"])
        if sequence_length <= 0:
            sequence_length = 144

        # 1. 加载时间序列并应用窗口限制
        series = self._load_timeseries(filename, area_column)
        series = series.astype(float).replace([np.inf, -np.inf], np.nan).dropna()

        days_window = int(default_params.get("days_window", 0))
        if days_window > 0:
            max_points = days_window * 144
            if len(series) > max_points:
                series = series.iloc[-max_points:]

        if len(series) <= sequence_length + 10:
            raise ValueError("时间序列长度不足以构造 CNN 训练样本，请提供更多数据")

        # 2. 归一化到 [-1, 1]
        scaler = MinMaxScaler(feature_range=(-1, 1))
        scaled_data = scaler.fit_transform(series.values.reshape(-1, 1)).flatten()

        # 3. 构造序列样本 (num_samples, sequence_length)
        X_all, y_all = self._create_sequences(scaled_data, sequence_length)
        if len(X_all) < 50:
            raise ValueError(f"数据量不足，需要至少50个序列，当前只有{len(X_all)}个")

        total_samples = len(X_all)
        train_size = int(total_samples * 0.75)
        test_size = total_samples - train_size
        if train_size <= 0 or test_size <= 0:
            raise ValueError("CNN 训练/测试样本数不足，请检查时间序列长度")

        X_train_np = X_all[:train_size]
        X_test_np = X_all[train_size:]
        y_train_np = y_all[:train_size]
        y_test_np = y_all[train_size:]

        # 转为张量，CNN 输入为 (batch, channels=1, seq_len)
        X_train = torch.FloatTensor(X_train_np).unsqueeze(1)
        y_train = torch.FloatTensor(y_train_np).unsqueeze(-1)
        X_test = torch.FloatTensor(X_test_np).unsqueeze(1)

        train_dataset = TensorDataset(X_train, y_train)
        train_loader = DataLoader(
            train_dataset,
            batch_size=int(default_params["batch_size"]),
            shuffle=True,
        )

        class CNN1DModel(nn.Module):
            def __init__(
                self,
                in_channels: int = 1,
                num_filters: int = 32,
                kernel_size: int = 5,
                num_layers: int = 2,
                hidden_size: int = 64,
                dropout: float = 0.1,
            ) -> None:
                super().__init__()

                layers: list[nn.Module] = []
                current_channels = in_channels
                padding = max(kernel_size // 2, 0)
                for i in range(num_layers):
                    conv = nn.Conv1d(
                        in_channels=current_channels,
                        out_channels=num_filters,
                        kernel_size=kernel_size,
                        padding=padding,
                    )
                    layers.append(conv)
                    layers.append(nn.ReLU())
                    current_channels = num_filters

                self.conv = nn.Sequential(*layers)
                self.dropout = nn.Dropout(dropout)
                self.fc = nn.Linear(num_filters * sequence_length, hidden_size)
                self.out = nn.Linear(hidden_size, 1)

            def forward(self, x: torch.Tensor) -> torch.Tensor:  # type: ignore[override]
                # x: (batch, 1, seq_len)
                feat = self.conv(x)
                feat = feat.view(feat.size(0), -1)
                feat = self.dropout(feat)
                feat = torch.relu(self.fc(feat))
                return self.out(feat)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("CNN 使用设备: %s", device)

        model = CNN1DModel(
            in_channels=1,
            num_filters=int(default_params["num_filters"]),
            kernel_size=int(default_params["kernel_size"]),
            num_layers=int(default_params["num_layers"]),
            hidden_size=int(default_params["hidden_size"]),
            dropout=float(default_params["dropout"]),
        ).to(device)

        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=float(default_params["learning_rate"]))

        best_loss = float("inf")
        patience_counter = 0

        for epoch in range(int(default_params["epochs"])):
            model.train()
            total_loss = 0.0
            for batch_X, batch_y in train_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)

                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

                total_loss += float(loss.item())

            avg_loss = total_loss / max(len(train_loader), 1)
            if avg_loss < best_loss:
                best_loss = avg_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= int(default_params["early_stopping_patience"]):
                    logger.info("CNN 早停于第 %d 轮, 最佳训练损失 %.6f", epoch + 1, best_loss)
                    break

        model.eval()
        with torch.no_grad():
            train_pred_t = model(X_train.to(device)).cpu().numpy()
            test_pred_t = model(X_test.to(device)).cpu().numpy()

        # 未来预测：使用递归方式基于最后一个窗口逐步预测
        with torch.no_grad():
            last_seq = torch.FloatTensor(
                scaled_data[-sequence_length:]
            ).view(1, 1, sequence_length).to(device)
            future_steps = max(1, sequence_length // 8)
            future_scaled: list[float] = []

            current_seq = last_seq.clone()
            for _ in range(future_steps):
                pred = model(current_seq)[:, 0].cpu().numpy()[0]
                future_scaled.append(float(pred))

                seq_np = current_seq.cpu().numpy()
                seq_np = np.roll(seq_np, -1, axis=2)
                seq_np[0, 0, -1] = pred
                current_seq = torch.FloatTensor(seq_np).to(device)

        # 反归一化
        test_pred = scaler.inverse_transform(test_pred_t).flatten()
        future_pred = scaler.inverse_transform(
            np.array(future_scaled).reshape(-1, 1)
        ).flatten()

        y_train_inv = scaler.inverse_transform(y_train_np.reshape(-1, 1)).flatten()
        y_test_inv = scaler.inverse_transform(y_test_np.reshape(-1, 1)).flatten()

        # 构造索引，考虑 sequence_length 偏移
        history_index = series.index.tolist()
        effective_start = sequence_length
        effective_end = sequence_length + train_size + test_size
        if effective_end > len(history_index):
            effective_end = len(history_index)

        train_index = history_index[effective_start : effective_start + train_size]
        test_index = history_index[
            effective_start + train_size : effective_start + train_size + test_size
        ]

        # 未来时间索引
        if len(history_index) > 0:
            last_time = pd.to_datetime(history_index[-1])
            freq = pd.infer_freq(history_index)
            if freq:
                future_index = pd.date_range(
                    start=last_time, periods=future_steps + 1, freq=freq
                )[1:].tolist()
            else:
                future_index = pd.date_range(
                    start=last_time, periods=future_steps + 1, freq="10min"
                )[1:].tolist()
        else:
            future_index = list(range(future_steps))

        return {
            "area": area_column,
            "history_index": history_index,
            "history_values": series.values.tolist(),
            "train_index": train_index,
            "train_values": y_train_inv.tolist(),
            "test_index": test_index,
            "test_values": y_test_inv.tolist(),
            "test_pred_values": test_pred.tolist(),
            "future_index": future_index,
            "future_forecast_values": future_pred.tolist(),
            "metrics": {
                "mae": float(mean_absolute_error(y_test_inv, test_pred)),
                "mse": float(mean_squared_error(y_test_inv, test_pred)),
                "rmse": float(
                    mean_squared_error(y_test_inv, test_pred, squared=False)
                ),
            },
        }

    def _create_sequences(self, data: np.ndarray, sequence_length: int):
        """创建LSTM序列数据"""
        X, y = [], []
        for i in range(sequence_length, len(data)):
            X.append(data[i-sequence_length:i])
            y.append(data[i])
        return np.array(X), np.array(y)


# 创建全局服务实例
prediction_service = PredictionService()




















