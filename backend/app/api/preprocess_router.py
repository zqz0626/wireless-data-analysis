from fastapi import APIRouter, HTTPException, Body, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from typing import List, Dict, Any, Tuple, Union
import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from app.services.preprocess_service import preprocess_service
from app.api.file_router import file_db, save_file_db, init_file_db  # 导入文件数据库与持久化函数

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 确保文件数据库已初始化
init_file_db()

# 辅助函数：递归处理所有可能的特殊值，确保能被JSON序列化
def make_json_serializable(obj: Any) -> Any:
    """
    递归处理所有可能的特殊值，确保能被JSON序列化
    """
    if obj is None or isinstance(obj, (str, int, bool)):
        return obj
    elif isinstance(obj, float):
        # 处理无穷大和NaN值
        if np.isinf(obj) or np.isnan(obj):
            return None
        return obj
    elif isinstance(obj, np.number):
        # 处理numpy数值类型
        return obj.item()
    elif isinstance(obj, np.ndarray):
        # 处理numpy数组
        return [make_json_serializable(item) for item in obj.tolist()]
    elif isinstance(obj, dict):
        # 递归处理字典
        return {key: make_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        # 递归处理列表
        return [make_json_serializable(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        # 处理对象
        return make_json_serializable(obj.__dict__)
    else:
        # 尝试转换为字符串
        try:
            return str(obj)
        except:
            return None

router = APIRouter()

# 同时支持无斜杠和带斜杠两种路径形式，避免反向代理/前端差异导致 404
@router.post("", summary="数据预处理")
@router.post("/", summary="数据预处理（兼容带斜杠）")
async def preprocess_data(
    file_id: str = Body(..., description="文件ID"),
    operations: List[Dict[str, Any]] = Body(..., description="预处理操作列表")
):
    """
    对指定文件进行数据预处理
    """
    start_time = datetime.now()
    
    try:
        # 验证文件ID格式
        if not file_id or not isinstance(file_id, str):
            raise HTTPException(
                status_code=400,
                detail="无效的文件ID"
            )
        
        # 验证操作列表
        if not isinstance(operations, list):
            raise HTTPException(
                status_code=400,
                detail="预处理操作必须是列表格式"
            )
        
        # 查找文件
        logger.info(f"查找文件: {file_id}")
        file_info = next((f for f in file_db if f["id"] == file_id), None)
        if not file_info:
            logger.error(f"文件不存在: {file_id}")
            raise HTTPException(
                status_code=404,
                detail=f"文件不存在: {file_id}"
            )
        
        logger.info(f"找到文件: {file_info['original_filename']}, 路径: {file_info['path']}")
        
        # 调用预处理服务，确保使用绝对路径
        file_absolute_path = os.path.abspath(file_info["path"])
        logger.info(f"开始预处理，文件路径: {file_absolute_path}, 操作数: {len(operations)}")
        
        # 将前端操作列表转换为服务层需要的标准格式
        def normalize_operations(raw_ops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            normalized: List[Dict[str, Any]] = []
            
            for op in raw_ops or []:
                if not isinstance(op, dict):
                    continue
                    
                op_type = op.get("type")
                # 统一操作类型为小写
                if isinstance(op_type, str):
                    op_type = op_type.strip().lower()
                else:
                    continue

                # 处理缺失值（兼容前端handle_missing_values类型）
                if op_type == "handle_missing_values":
                    strategy = (op.get("strategy") or "").strip().lower()
                    columns = op.get("columns")
                    
                    # 删除包含缺失值的行
                    if strategy in ("skip", "drop"):
                        normalized.append({
                            "type": "drop_null",
                            "parameters": {
                                "axis": "rows",
                                "how": "any",
                                "columns": columns
                            }
                        })
                    # 填充缺失值
                    elif strategy in ("mean", "median", "mode", "ffill", "constant"):
                        params = {
                            "method": "constant" if strategy == "constant" else strategy,
                            "columns": columns
                        }
                        if strategy == "constant" and "value" in op:
                            params["value"] = op.get("value")
                        normalized.append({
                            "type": "fill_null",
                            "parameters": params
                        })

                # 处理标准化操作
                elif op_type == "standardize":
                    # 合并parameters和直接在op中的参数，优先使用parameters
                    p = op.get("parameters", {}) if isinstance(op.get("parameters"), dict) else {}
                    params = {}
                    
                    # 获取方法和列参数
                    params["method"] = p.get("method", op.get("method", "zscore"))
                    params["columns"] = p.get("columns", op.get("columns"))
                    # 小数位数（可选），用于控制标准化结果保留的小数位
                    if "decimal_places" in p or "decimal_places" in op:
                        params["decimal_places"] = p.get("decimal_places", op.get("decimal_places"))
                    
                    normalized.append({
                        "type": "standardize",
                        "parameters": params
                    })

                # 直接支持服务层原生操作类型
                elif op_type in ("drop_null", "fill_null", "standardize"):
                    # 提取所有非type参数
                    other_params = {k: v for k, v in op.items() if k != "type"}
                    normalized.append({
                        "type": op_type,
                        "parameters": other_params.get("parameters", other_params)
                    })

            return normalized

        normalized_ops = normalize_operations(operations)

        try:
            processed_file_id, processed_file_path, processed_df, service_stats = preprocess_service.apply_operations(
                file_absolute_path,
                file_info["extension"],
                normalized_ops
            )
            logger.info(f"预处理成功完成，处理后文件ID: {processed_file_id}")
        except Exception as e:
            logger.error(f"预处理服务执行失败: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"预处理执行失败: {str(e)}"
            )
        
        # 验证处理结果
        if not processed_file_id or not processed_file_path:
            raise HTTPException(
                status_code=500,
                detail="预处理服务返回无效结果"
            )
        
        # 确保处理后的文件存在
        if not os.path.exists(processed_file_path):
            raise HTTPException(
                status_code=500,
                detail="处理后的文件创建失败"
            )
        
        # 生成唯一的输出文件名（避免重名）
        base_name = file_info["original_filename"].replace(f".{file_info['extension']}", "")
        extension = file_info["extension"]
        existing_names = {f["original_filename"] for f in file_db}
        
        # 尝试 base_name_processed.ext，如果重复则追加 (n)
        output_name = f"{base_name}_processed.{extension}"
        if output_name in existing_names:
            n = 1
            while f"{base_name}_processed({n}).{extension}" in existing_names:
                n += 1
            output_name = f"{base_name}_processed({n}).{extension}"
        
        # 创建处理后文件的信息
        processed_file_size = os.path.getsize(processed_file_path)
        processed_file_info = {
            "id": processed_file_id,
            "original_filename": output_name,
            "filename": os.path.basename(processed_file_path),
            "path": processed_file_path,
            "size": processed_file_size,
            "upload_time": datetime.now().isoformat(),
            "extension": file_info["extension"],
            "parent_file_id": file_id,  # 记录父文件ID
            # 预处理后的文件依旧是数据文件
            "file_type": "data"
        }

        # 如果原始数据文件已经关联了 GeoJSON，也继承这条关联
        if file_info.get("related_geojson_id"):
            processed_file_info["related_geojson_id"] = file_info["related_geojson_id"]
        
        # 添加到模拟数据库并持久化
        try:
            file_db.append(processed_file_info)
            # 将变更持久化到磁盘
            try:
                save_file_db()
            except Exception as e:
                # 如果持久化失败，回滚内存并删除已保存的文件，避免悬挂文件引用
                logger.error(f"持久化 file_db 失败: {str(e)}")
                # 回滚内存中的记录
                try:
                    file_db.remove(processed_file_info)
                except Exception:
                    pass
                # 删除已保存的处理文件（如果存在）
                try:
                    if os.path.exists(processed_file_path):
                        os.remove(processed_file_path)
                except Exception:
                    logger.warning("回滚时未能删除处理文件")
                raise HTTPException(status_code=500, detail=f"持久化处理结果失败: {str(e)}")

            logger.info(f"已将处理后的文件添加到数据库并持久化: {processed_file_id}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"添加处理后文件到 file_db 失败: {str(e)}", exc_info=True)
            # 尝试删除文件以避免残留
            try:
                if os.path.exists(processed_file_path):
                    os.remove(processed_file_path)
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"保存处理后文件信息失败: {str(e)}")
        
        # 合并服务返回的统计信息和基本信息
        stats = {
            "original_rows": service_stats.get("original_rows", 0),
            "original_columns": service_stats.get("original_columns", 0),
            "processed_rows": service_stats.get("processed_rows", 0),
            "processed_columns": service_stats.get("processed_columns", 0),
            "columns": list(processed_df.columns) if not processed_df.empty else [],
            "operations_applied": service_stats.get("operations_applied", 0),
            "operations_failed": service_stats.get("operations_failed", 0),
            "missing_values_handled": service_stats.get("missing_values_handled", 0),
            "outliers_removed": service_stats.get("outliers_removed", 0),
            "outliers_clipped": service_stats.get("outliers_clipped", 0),
            "duplicates_removed": service_stats.get("duplicates_removed", 0),
            "features_selected": service_stats.get("features_selected", 0),
            "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000)
        }
        
        # 添加额外的统计信息（如果有）
        if 'dtype_distribution' in service_stats:
            stats['dtype_distribution'] = service_stats['dtype_distribution']
        if 'numeric_columns_count' in service_stats:
            stats['numeric_columns_count'] = service_stats['numeric_columns_count']
        
        # 获取样本数据并处理特殊值
        sample_df = processed_df.head(10).copy() if not processed_df.empty else pd.DataFrame()
        
        # 更严格地处理DataFrame中的所有特殊值
        for col in sample_df.columns:
            # 首先处理数值列中的特殊值
            if sample_df[col].dtype.kind in 'ifc':  # integer, float, complex
                # 将inf和-ninf替换为None
                sample_df[col] = sample_df[col].replace([np.inf, -np.inf], None)
                # 将NaN替换为None
                sample_df[col] = sample_df[col].where(pd.notna(sample_df[col]), None)
            # 处理字符串列中的None值
            elif pd.api.types.is_string_dtype(sample_df[col]):
                sample_df[col] = sample_df[col].fillna('')
        
        # 额外的处理：将整个DataFrame中的所有numpy类型转换为Python原生类型
        for col in sample_df.columns:
            # 处理数值列
            if pd.api.types.is_numeric_dtype(sample_df[col]):
                sample_df[col] = sample_df[col].apply(lambda x: float(x) if isinstance(x, np.number) and not pd.isna(x) else x)
            # 处理布尔列
            elif pd.api.types.is_bool_dtype(sample_df[col]):
                sample_df[col] = sample_df[col].astype(bool)
            # 处理其他类型
            else:
                sample_df[col] = sample_df[col].astype(object).where(pd.notna(sample_df[col]), None)
        
        # 将DataFrame转换为字典并确保所有值都可序列化
        sample_data = []
        for _, row in sample_df.iterrows():
            row_dict = {}
            for col, val in row.items():
                if pd.isna(val):
                    row_dict[col] = None
                elif isinstance(val, np.number):
                    # 确保numpy数值类型转换为Python原生类型
                    row_dict[col] = float(val) if isinstance(val, np.floating) else int(val)
                elif isinstance(val, np.ndarray):
                    row_dict[col] = val.tolist()
                elif isinstance(val, (np.integer, np.floating, np.bool_)):
                    row_dict[col] = val.item()
                else:
                    row_dict[col] = val
            sample_data.append(row_dict)
        
        # 构建响应数据
        response_data = {
            "success": True,
            "message": "数据预处理成功",
            "data": {
                "file_id": file_id,
                "processed_file_id": processed_file_id,
                "operations": operations,
                "stats": stats,
                "sample_data": sample_data
            }
        }
        
        # 先使用自定义函数处理所有特殊值
        serializable_data = make_json_serializable(response_data)
        
        logger.info(f"返回预处理结果，处理时间: {stats['processing_time_ms']}ms")
        return serializable_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预处理请求处理失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"数据预处理请求处理失败: {str(e)}"
        )
    finally:
        logger.info(f"预处理请求结束，总耗时: {(datetime.now() - start_time).total_seconds():.2f}s")

# 为避免误发 GET 到 /api/preprocess 时出现 404，这里返回清晰提示
@router.get("", summary="预处理端点说明")
@router.get("/", summary="预处理端点说明（兼容带斜杠）")
async def preprocess_help():
    return {
        "success": False,
        "message": "请使用 POST /api/preprocess 提交 {file_id, operations} 进行数据预处理。若需获取可选项，请调用 GET /api/preprocess/options",
    }

@router.get("/options", summary="获取预处理选项")
async def get_preprocess_options():
    """
    获取可用的预处理操作选项
    """
    return {
        "success": True,
        "data": {
            "options": [
                {
                    "type": "drop_null",
                    "name": "删除空值",
                    "description": "删除包含空值的行或列",
                    "parameters": [
                        {
                            "name": "axis",
                            "type": "string",
                            "options": ["rows", "columns"],
                            "default": "rows"
                        },
                        {
                            "name": "how",
                            "type": "string",
                            "options": ["any", "all"],
                            "default": "any"
                        }
                    ]
                },
                {
                    "type": "fill_null",
                    "name": "填充空值",
                    "description": "用指定值填充空值",
                    "parameters": [
                        {
                            "name": "method",
                            "type": "string",
                            "options": ["mean", "median", "constant"],
                            "default": "mean"
                        },
                        {
                            "name": "value",
                            "type": "number",
                            "description": "当method为constant时的填充值"
                        },
                        {
                            "name": "columns",
                            "type": "array",
                            "description": "要处理的列，默认处理所有数值列"
                        }
                    ]
                },
                
                {
                    "type": "standardize",
                    "name": "数据标准化",
                    "description": "将数据标准化或归一化",
                    "parameters": [
                        {
                            "name": "method",
                            "type": "string",
                            "options": ["zscore", "minmax"],
                            "description": "标准化方法：zscore(Z分数)或minmax(最小最大归一化)",
                            "default": "zscore"
                        },
                        {
                            "name": "columns",
                            "type": "array",
                            "description": "要处理的列，默认处理所有数值列"
                        }
                    ]
                }
            ]
        }
    }
