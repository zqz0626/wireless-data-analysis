"""数据预处理服务：只负责缺失值处理和标准化。"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class PreprocessService:
    """数据预处理服务类（精简版）"""

    def __init__(self) -> None:
        self.upload_dir = Path(__file__).parent.parent.parent / "uploads"
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    # 基础 I/O -------------------------------------------------------------
    def read_file(self, file_path: str, extension: str) -> pd.DataFrame:
        """读取 CSV / Excel 文件。"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if extension == "csv":
            return pd.read_csv(file_path)
        if extension in ("xlsx", "xls"):
            return pd.read_excel(file_path)
        raise ValueError(f"不支持的文件格式: {extension}")

    def save_file(self, df: pd.DataFrame, extension: str, source_file_path: str) -> Tuple[str, str]:
        """保存预处理后的文件，在 uploads 目录下生成不重名的文件。"""
        base_name = os.path.splitext(os.path.basename(source_file_path))[0]
        invalid_chars = set('<>:"/\\|?*')
        safe_base = "".join(ch for ch in base_name if ch not in invalid_chars).strip().rstrip(".") or "processed"
        file_id = f"{safe_base}_processed"

        filename = f"{file_id}.{extension}"
        file_path = self.upload_dir / filename
        counter = 1
        while file_path.exists():
            file_id = f"{safe_base}_processed({counter})"
            filename = f"{file_id}.{extension}"
            file_path = self.upload_dir / filename
            counter += 1

        if extension == "csv":
            df.to_csv(file_path, index=False)
        elif extension in ("xlsx", "xls"):
            df.to_excel(file_path, index=False)
        else:
            file_path = file_path.with_suffix(".csv")
            df.to_csv(file_path, index=False)

        return file_id, str(file_path)

    # 预处理原子操作 -------------------------------------------------------
    def drop_null(
        self,
        df: pd.DataFrame,
        axis: str = "rows",
        how: str = "any",
        columns: Optional[List[str]] = None,
    ) -> Tuple[pd.DataFrame, int]:
        """删除空值。

        仅当显式指定 columns 时生效，返回新 DataFrame 和删除的行数。"""

        df_copy = df.copy()
        if not columns:
            return df_copy, 0

        if axis == "rows":
            df_clean = df_copy.dropna(subset=columns, how=how)
        else:
            axis_num = 0 if axis == "rows" else 1
            df_clean = df_copy.dropna(axis=axis_num, how=how)

        return df_clean, int(len(df) - len(df_clean))

    def fill_null(
        self,
        df: pd.DataFrame,
        method: str = "mean",
        value: Optional[float] = None,
        columns: Optional[List[str]] = None,
    ) -> Tuple[pd.DataFrame, int]:
        """填充空值。

        仅当显式指定 columns 时生效，返回新 DataFrame 和被填充的单元格数量。"""

        df_copy = df.copy()
        if not columns:
            return df_copy, 0

        cols = [col for col in columns if col in df_copy.columns]
        missing_count = 0
        for col in cols:
            missing_before = df_copy[col].isnull().sum()
            if missing_before == 0:
                continue

            if method == "mean" and pd.api.types.is_numeric_dtype(df_copy[col]):
                fill_value = df_copy[col].mean()
            elif method == "median" and pd.api.types.is_numeric_dtype(df_copy[col]):
                fill_value = df_copy[col].median()
            elif method == "constant" and value is not None:
                fill_value = value if pd.api.types.is_numeric_dtype(df_copy[col]) else str(value)
            elif method == "mode":
                mode_values = df_copy[col].mode()
                fill_value = mode_values.iloc[0] if not mode_values.empty else None
            else:
                df_copy[col] = df_copy[col].fillna(method="ffill")
                missing_count += int(missing_before)
                continue

            if fill_value is not None:
                df_copy[col] = df_copy[col].fillna(fill_value)
                missing_count += int(missing_before)

        return df_copy, missing_count

    def standardize(
        self,
        df: pd.DataFrame,
        method: str = "zscore",
        columns: Optional[List[str]] = None,
        decimal_places: int = 7,
    ) -> pd.DataFrame:
        """数据标准化：zscore 或 minmax。

        未指定 columns 时，默认对所有数值列进行标准化。"""

        df_copy = df.copy()
        if not columns:
            cols = list(df_copy.select_dtypes(include=[np.number]).columns)
        else:
            cols = [col for col in columns if col in df_copy.columns]

        if not cols:
            return df_copy

        for col in cols:
            if method == "zscore":
                mean_val = df_copy[col].mean()
                std_val = df_copy[col].std()
                if std_val > 0:
                    df_copy[col] = (df_copy[col] - mean_val) / std_val
            elif method == "minmax":
                min_val = df_copy[col].min()
                max_val = df_copy[col].max()
                if max_val > min_val:
                    df_copy[col] = (df_copy[col] - min_val) / (max_val - min_val)

            # 如果指定了保留小数位数，则对该列进行四舍五入
            if isinstance(decimal_places, int) and decimal_places >= 0:
                try:
                    df_copy[col] = df_copy[col].round(decimal_places)
                except Exception:
                    # 某些非常规类型列（如混合类型）round 可能失败，忽略即可
                    pass

        return df_copy

    # 主调度函数 -----------------------------------------------------------
    def apply_operations(
        self,
        file_path: str,
        extension: str,
        operations: List[Dict[str, Any]],
    ) -> Tuple[str, str, pd.DataFrame, Dict[str, Any]]:
        """按顺序应用预处理操作，只支持 drop_null / fill_null / standardize。"""

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        df = self.read_file(file_path, extension)
        initial_rows, initial_cols = len(df), len(df.columns)

        stats: Dict[str, Any] = {
            "original_rows": initial_rows,
            "original_columns": initial_cols,
            "processed_rows": initial_rows,
            "processed_columns": initial_cols,
            "missing_values_handled": 0,
            "operations_applied": 0,
            "operations_failed": 0,
        }

        for operation in operations or []:
            op_type = (operation or {}).get("type")
            params = (operation or {}).get("parameters", {}) or {}

            try:
                if op_type == "drop_null":
                    df, handled = self.drop_null(df, **params)
                    stats["missing_values_handled"] += int(handled)
                    stats["processed_rows"] = len(df)
                elif op_type == "fill_null":
                    df, handled = self.fill_null(df, **params)
                    stats["missing_values_handled"] += int(handled)
                elif op_type == "standardize":
                    df = self.standardize(df, **params)
                else:
                    # 未知操作类型直接跳过
                    stats["operations_failed"] += 1
                    continue

                stats["operations_applied"] += 1
            except Exception:
                stats["operations_failed"] += 1

        stats["processed_rows"] = len(df)
        stats["processed_columns"] = len(df.columns)

        file_id, new_path = self.save_file(df, extension, file_path)
        return file_id, new_path, df, stats


preprocess_service = PreprocessService()
