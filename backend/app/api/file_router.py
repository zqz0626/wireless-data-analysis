"""
文件管理路由
负责处理文件上传、下载、预览、删除等文件相关操作
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Body
from fastapi.responses import FileResponse
from fastapi.encoders import jsonable_encoder
import os
import uuid
import pandas as pd
import numpy as np
from datetime import datetime
import json
import re
import zipfile
import tempfile
from typing import List, Dict, Any, Union, Set
import logging

"""
创建文件管理路由实例
"""
router = APIRouter()

"""
创建日志记录器
"""
logger = logging.getLogger(__name__)

# 辅助函数：递归处理所有可能的特殊值，确保能被JSON序列化
def make_json_serializable(obj: Any) -> Any:
    """
    递归处理所有可能的特殊值，确保能被JSON序列化
    处理numpy类型、NaN、Infinity等特殊值
    """
    # 处理None
    if obj is None:
        return None
    
    # 处理numpy类型 - 优先级最高，因为numpy类型可能会被误识别为其他类型
    if isinstance(obj, np.ndarray):
        # 先转换为Python列表，再递归处理每个元素
        return [make_json_serializable(item) for item in obj.tolist()]
    elif isinstance(obj, np.bool_):
        # 特别处理numpy布尔类型
        return bool(obj)
    elif isinstance(obj, (np.integer, np.unsignedinteger)):
        # 处理所有numpy整数类型
        return int(obj)
    elif isinstance(obj, np.floating):
        # 处理所有numpy浮点数类型
        if np.isnan(obj):
            return None
        if np.isinf(obj):
            return 999999  # 用一个大数值代替正无穷
        if np.isneginf(obj):
            return -999999  # 用一个小数值代替负无穷
        return float(obj)
    
    # 处理基本类型
    elif isinstance(obj, (int, bool, str)):
        return obj
    
    # 处理浮点数特殊值
    elif isinstance(obj, float):
        if pd.isna(obj):  # 处理NaN, NaT等
            return None
        if np.isinf(obj):  # 处理Infinity
            return 999999
        if np.isneginf(obj):  # 处理-Infinity
            return -999999
        return obj
    
    # 处理字典
    elif isinstance(obj, dict):
        # 确保键是字符串
        return {str(key): make_json_serializable(value) for key, value in obj.items()}
    
    # 处理列表或元组
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    
    # 处理pandas的特殊类型
    elif isinstance(obj, pd.Series):
        return make_json_serializable(obj.to_dict())
    elif isinstance(obj, pd.DataFrame):
        return make_json_serializable(obj.to_dict(orient='records'))
    
    # 处理具有tolist方法的对象
    elif hasattr(obj, 'tolist'):
        try:
            return make_json_serializable(obj.tolist())
        except:
            pass
    
    # 处理datetime对象
    elif isinstance(obj, datetime):
        return obj.isoformat()
    
    # 其他类型尝试转换为字符串
    try:
        # 尝试使用json.dumps检查是否可序列化
        import json
        json.dumps(obj)
        return obj
    except:
        try:
            return str(obj)
        except:
            return "<unserializable object>"


# 上传文件保存路径 - 使用绝对路径确保正确性
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
# 确保上传目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)

# file_db 持久化路径
FILE_DB_PATH = os.path.join(UPLOAD_DIR, "file_db.json")

# 支持的文件类型
ALLOWED_CSV_EXTENSIONS = [".csv", ".xlsx", ".xls"]
ALLOWED_GEOJSON_EXTENSIONS = [".geojson", ".json"]
ALLOWED_ALL_EXTENSIONS = ALLOWED_CSV_EXTENSIONS + ALLOWED_GEOJSON_EXTENSIONS

# 加载持久化的 file_db（如果存在），否则使用空列表
def load_file_db():
    global file_db
    if os.path.exists(FILE_DB_PATH):
        try:
            with open(FILE_DB_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    # 过滤掉持久化文件自身（file_db.json）如果不小心被记录为上传文件
                    persisted = data
                    try:
                        file_db_basename = os.path.basename(FILE_DB_PATH)
                        persisted = [
                            item
                            for item in persisted
                            if item.get('filename') != file_db_basename
                            and item.get('original_filename') != file_db_basename
                            and os.path.abspath(str(item.get('path', ''))) != os.path.abspath(FILE_DB_PATH)
                        ]
                    except Exception:
                        # 如果结构不符合预期，跳过过滤
                        pass
                    file_db = persisted
                else:
                    # 如果格式异常，忽略并从空开始
                    file_db = []
        except Exception as e:
            print(f"加载 file_db 失败: {e}")
            file_db = []
    else:
        file_db = []








def save_file_db():
    # 使用原子替换确保写入安全
    try:
        tmp_path = FILE_DB_PATH + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(file_db, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, FILE_DB_PATH)
    except Exception as e:
        print(f"保存 file_db 失败: {e}")
# 模拟数据库，存储文件信息
file_db = []

# 初始化函数，加载uploads文件夹中已存在的文件
def init_file_db():
    """初始化文件数据库，先从持久化文件加载，再扫描 uploads 目录补充新文件"""
    # 先从磁盘加载已保存的 file_db
    load_file_db()

    # 扫描 uploads 目录，添加磁盘上但未记录的文件（按"路径"去重，避免不同ID策略导致的重复）
    changed = False
    # 接受的数据文件扩展名（包括GeoJSON）
    allowed_extensions = {'.csv', '.xls', '.xlsx', '.geojson', '.json'}
    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.isfile(file_path):
            # 跳过持久化文件本身
            if filename == os.path.basename(FILE_DB_PATH):
                continue
            # 提取文件ID和扩展名
            file_extension = os.path.splitext(filename)[1].lower()
            file_id = os.path.splitext(filename)[0]

            # 只处理允许的扩展名，跳过其他文件
            if file_extension not in allowed_extensions:
                continue

            # 检查文件是否已在数据库中：按绝对路径匹配，避免因 id 策略不同（UUID/文件名）造成重复
            if not any(os.path.abspath(file_info.get('path', '')) == os.path.abspath(file_path) for file_info in file_db):
                try:
                    file_size = os.path.getsize(file_path)
                    # 如果无法恢复原始文件名，则使用磁盘上的文件名作为原始名（更直观）
                    file_info = {
                        "id": file_id,
                        "original_filename": filename,
                        "filename": filename,
                        "path": file_path,
                        "size": file_size,
                        "upload_time": datetime.now().isoformat(),
                        "extension": file_extension[1:],
                        "file_type": "geojson" if file_extension in [".geojson", ".json"] else "data"
                    }
                    file_db.append(file_info)
                    print(f"加载现有文件: {filename}")
                    changed = True
                except Exception as e:
                    print(f"加载文件 {filename} 失败: {str(e)}")

    # 如果有变化，保存回持久化文件
    if changed:
        save_file_db()

# 初始化文件数据库
init_file_db()

@router.post("/upload", summary="上传单个文件")
async def upload_file(file: UploadFile = File(...)):
    """
    上传单个数据文件（支持CSV、Excel、GeoJSON格式）
    """
    return await _upload_single_file(file)





async def _upload_single_file(file: UploadFile):
    """
    上传单个文件的内部函数
    """
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    if file_extension not in ALLOWED_ALL_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。支持的格式: {', '.join(ALLOWED_ALL_EXTENSIONS)}"
        )
    
    # 业务规则：不允许上传与现有文件同名的文件（以 original_filename 判定）
    existing_same_name = next(
        (f for f in file_db if str(f.get("original_filename")) == str(file.filename)),
        None
    )
    if existing_same_name:
        raise HTTPException(
            status_code=400,
            detail=f"已存在同名文件: {file.filename}，请先删除或重命名后再上传"
        )
    
    # 基于原始文件名生成清洗后的根名，作为文件ID与磁盘名根；必要时通过 (n) 去重
    orig_basename = os.path.basename(file.filename or "")
    name_root, name_ext = os.path.splitext(orig_basename)
    # 统一扩展名为已校验过的 file_extension
    name_ext = file_extension

    # Windows/Unix 受限字符集合
    invalid_chars = set('<>:"/\\|?*')
    safe_root = ''.join(ch for ch in name_root if ch not in invalid_chars).strip().rstrip('.')
    if not safe_root:
        # 回退根名，确保可读性
        safe_root = "file"

    candidate = f"{safe_root}{name_ext}"
    candidate_path = os.path.join(UPLOAD_DIR, candidate)
    counter = 1
    while os.path.exists(candidate_path):
        candidate = f"{safe_root}({counter}){name_ext}"
        candidate_path = os.path.join(UPLOAD_DIR, candidate)
        counter += 1

    filename = candidate
    file_path = candidate_path
    
    # 保存文件
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 读取文件信息
        file_size = os.path.getsize(file_path)
        # 以磁盘文件名（去扩展名）作为全局唯一ID
        file_id = os.path.splitext(filename)[0]
        # 确保ID唯一（极端情况下防御）：
        if any(f.get('id') == file_id for f in file_db):
            # 追加时间戳后缀防御碰撞
            file_id = f"{file_id}_{int(datetime.now().timestamp())}"
        
        file_type = "geojson" if file_extension in ALLOWED_GEOJSON_EXTENSIONS else "data"
        
        file_info = {
            "id": file_id,
            "original_filename": file.filename,
            "filename": filename,
            "path": file_path,
            "size": file_size,
            "upload_time": datetime.now().isoformat(),
            "extension": file_extension[1:],
            "file_type": file_type
        }

        # 添加到模拟数据库
        file_db.append(file_info)
        # 持久化 file_db
        save_file_db()

        response_data = {
            "success": True,
            "message": "文件上传成功",
            "data": file_info
        }
        
        # 先使用自定义函数处理所有特殊值，然后再返回
        serializable_data = make_json_serializable(response_data)
        return serializable_data
    except Exception as e:
        # 如果出错，删除已上传的文件
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=500,
            detail=f"文件上传失败: {str(e)}"
        )

@router.get("", summary="获取文件列表")
async def get_file_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """
    获取已上传文件列表，支持分页
    """
    # 在分页前主动触发一次扫描，补录磁盘上新出现而未入库的文件
    try:
        init_file_db()
    except Exception:
        pass

    # 在分页前清理无效记录（磁盘上已不存在的文件）
    global file_db
    try:
        before = len(file_db)
        file_db = [f for f in file_db if f.get('path') and os.path.exists(f.get('path'))]
        if len(file_db) != before:
            save_file_db()
    except Exception as _:
        # 清理失败不影响正常返回
        pass

    # 按上传时间倒序排序，确保最新上传的文件出现在前面
    try:
        sorted_files = sorted(
            file_db,
            key=lambda f: str(f.get("upload_time", "")),
            reverse=True
        )
    except Exception:
        # 回退：如果排序失败，使用原始顺序
        sorted_files = list(file_db)

    # 计算分页
    start = (page - 1) * page_size
    end = start + page_size

    # 获取分页数据（基于排序后的列表）
    paged_files = sorted_files[start:end]

    response_data = {
        "success": True,
        "data": {
            "total": len(sorted_files),
            "page": page,
            "page_size": page_size,
            "files": paged_files
        }
    }
    
    # 使用make_json_serializable确保所有值都可JSON序列化
    return make_json_serializable(response_data)

@router.get("/{file_id}/preview", summary="预览文件内容")
async def preview_file(
    file_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    预览文件内容，支持分页
    """
    # 先触发一次扫描，确保file_db与磁盘文件一致
    try:
        init_file_db()
    except Exception:
        pass
    
    # 查找文件
    file_info = next((f for f in file_db if f["id"] == file_id), None)
    
    # 如果file_db中找不到文件，尝试直接在磁盘上查找
    if not file_info:
        # 尝试在uploads目录中查找匹配file_id的文件
        for filename in os.listdir(UPLOAD_DIR):
            if os.path.splitext(filename)[0] == file_id:
                file_path = os.path.join(UPLOAD_DIR, filename)
                if os.path.exists(file_path):
                    # 创建临时file_info
                    file_extension = os.path.splitext(filename)[1].lower()
                    file_info = {
                        "id": file_id,
                        "original_filename": filename,
                        "filename": filename,
                        "path": file_path,
                        "size": os.path.getsize(file_path),
                        "upload_time": datetime.now().isoformat(),
                        "extension": file_extension[1:],
                        "file_type": "geojson" if file_extension in ALLOWED_GEOJSON_EXTENSIONS else "data"
                    }
                    # 添加到file_db
                    file_db.append(file_info)
                    save_file_db()
                    break
    
    if not file_info:
        raise HTTPException(
            status_code=404,
            detail="文件不存在"
        )
    
    try:
        file_path = file_info.get("path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="磁盘上找不到文件")

        # 根据扩展名选择读取方式（统一为小写并去除空白）
        ext = str(file_info.get("extension", "")).lower().strip()

        # 1) 表格型文件：CSV / Excel
        if ext in ("csv", "xlsx", "xls"):
            if ext == "csv":
                df = pd.read_csv(file_path)
            else:
                # Excel：兼容不同引擎
                try:
                    engine = "openpyxl" if ext == "xlsx" else "xlrd"
                    df = pd.read_excel(file_path, engine=engine)
                except ImportError as ie:
                    # 缺少依赖库
                    missing = "openpyxl" if ext == "xlsx" else "xlrd"
                    raise HTTPException(status_code=500, detail=f"文件预览失败: 需要安装依赖 {missing}") from ie
                except Exception:
                    # 引擎选择失败时，回退不指定 engine（让 pandas 自行选择）
                    df = pd.read_excel(file_path)

            # 获取数据信息
            total_rows = int(len(df))
            # 确保列名为字符串，避免 JSON 序列化问题
            columns = [str(c) for c in df.columns.tolist()]

            # 计算分页
            start = max((page - 1) * page_size, 0)
            end = start + page_size

            # 获取分页数据
            if start >= total_rows:
                page_df = df.head(0).copy()
            else:
                page_df = df.iloc[start:end].copy()

            # 将DataFrame中的所有特殊值（NaN, Inf, -Inf）转换为None
            # 使用更严格的方式处理所有可能的特殊值
            for col in page_df.columns:
                # 首先尝试将列转换为字符串，确保所有值都可以处理
                if page_df[col].dtype.kind in 'ifc':  # integer, float, complex
                    # 将inf和-ninf替换为None
                    page_df[col] = page_df[col].replace([np.inf, -np.inf], None)
                    # 将NaN替换为None
                    page_df[col] = page_df[col].where(pd.notna(page_df[col]), None)

            # 额外的处理：将整个DataFrame中的所有numpy类型转换为Python原生类型
            # 这可以确保所有值都能被JSON正确序列化
            for col in page_df.columns:
                # 处理数值列
                if pd.api.types.is_numeric_dtype(page_df[col]):
                    page_df[col] = page_df[col].apply(lambda x: float(x) if isinstance(x, np.number) else x)
                # 处理布尔列
                elif pd.api.types.is_bool_dtype(page_df[col]):
                    page_df[col] = page_df[col].astype(bool)
                # 处理其他类型
                else:
                    page_df[col] = page_df[col].astype(object).where(pd.notna(page_df[col]), None)

            # 转换为字典列表
            paged_data = page_df.to_dict(orient="records")

        # 2) 其他允许上传的文件（json / geojson）：按 JSON 方式预览
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"JSON 文件读取失败: {str(e)}")

            # GeoJSON FeatureCollection
            if isinstance(raw, dict) and isinstance(raw.get("features"), list):
                features = raw.get("features", [])
                total_rows = len(features)

                # 计算属性列集合
                prop_keys = set()
                for feat in features:
                    props = feat.get("properties") or {}
                    for k in props.keys():
                        prop_keys.add(str(k))

                columns = sorted(list(prop_keys)) + ["geometry_type"]

                # 分页
                start = max((page - 1) * page_size, 0)
                end = start + page_size
                page_feats = features[start:end]

                paged_data = []
                for feat in page_feats:
                    props = feat.get("properties") or {}
                    row = {str(k): props.get(k) for k in prop_keys}
                    geom = feat.get("geometry") or {}
                    row["geometry_type"] = geom.get("type")
                    paged_data.append(row)

            # 通用 JSON：列表或字典
            else:
                # 列表
                if isinstance(raw, list):
                    total_rows = len(raw)

                    # 统一取前若干行的键作为列
                    prop_keys = set()
                    for item in raw:
                        if isinstance(item, dict):
                            for k in item.keys():
                                prop_keys.add(str(k))

                    if prop_keys:
                        columns = sorted(list(prop_keys))
                        start = max((page - 1) * page_size, 0)
                        end = start + page_size
                        page_items = raw[start:end]
                        paged_data = []
                        for item in page_items:
                            if isinstance(item, dict):
                                row = {str(k): item.get(k) for k in prop_keys}
                            else:
                                row = {"value": item}
                            paged_data.append(row)
                        if not columns:
                            columns = ["value"]
                    else:
                        # 非字典元素的简单列表
                        columns = ["value"]
                        start = max((page - 1) * page_size, 0)
                        end = start + page_size
                        page_items = raw[start:end]
                        paged_data = [{"value": item} for item in page_items]

                # 单个字典：作为一行展示
                elif isinstance(raw, dict):
                    columns = [str(k) for k in raw.keys()]
                    total_rows = 1
                    paged_data = [raw]
                else:
                    # 其他标量类型
                    columns = ["value"]
                    total_rows = 1
                    paged_data = [{"value": raw}]
        
        # 使用jsonable_encoder确保所有值都可JSON序列化
        response_data = {
            "success": True,
            "data": {
                "file_info": file_info,
                "total_rows": int(total_rows),
                "page": page,
                "page_size": page_size,
                "columns": columns,
                "data": paged_data
            }
        }
        
        # 先使用自定义函数处理所有特殊值，然后再返回
        serializable_data = make_json_serializable(response_data)
        return serializable_data
    except Exception as e:
        # 如果已被上面转换为 HTTPException，直接抛出
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"文件预览失败: {str(e)}")


@router.get("/{file_id}/raw", summary="获取原始JSON/GeoJSON内容")
async def get_raw_json(file_id: str):
    """返回原始 JSON / GeoJSON 文件内容，供前端地图等组件直接使用。

    仅支持扩展名为 .json / .geojson 的文件，其它类型将返回 400。
    """
    # 查找文件
    file_info = next((f for f in file_db if f.get("id") == file_id), None)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")

    file_path = file_info.get("path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="磁盘上找不到文件")

    ext = str(file_info.get("extension", "")).lower().strip()
    if ext not in ("json", "geojson"):
        raise HTTPException(status_code=400, detail="仅支持 JSON/GeoJSON 文件的原始内容获取")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取原始文件内容失败: {str(e)}")

@router.delete("/{file_id}", summary="删除文件")
async def delete_file(file_id: str):
    """
    删除指定文件
    """
    global file_db
    # 查找待删除的文件
    file_to_delete = next((f for f in file_db if f.get("id") == file_id), None)
    if file_to_delete is None:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        # 删除磁盘上的文件
        file_path = file_to_delete.get("path")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                # 磁盘删除失败时记录错误
                logger.error(f"删除文件失败: {file_path} - {e}")

        # 从数据库中移除该文件
        file_db = [f for f in file_db if f.get("id") != file_id]

        # 持久化 file_db
        save_file_db()

        response_data = {"success": True, "message": "文件删除成功"}
        return make_json_serializable(response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件删除失败: {str(e)}")

@router.get("/{file_id}", summary="获取文件详细信息")
async def get_file_info(file_id: str):
    """
    获取文件的详细信息，包括元数据和数据统计
    """
    # 先触发一次扫描，确保file_db与磁盘文件一致
    try:
        init_file_db()
    except Exception:
        pass
    
    # 查找文件
    file_info = next((f for f in file_db if f["id"] == file_id), None)
    
    # 如果file_db中找不到文件，尝试直接在磁盘上查找
    if not file_info:
        # 尝试在uploads目录中查找匹配file_id的文件
        for filename in os.listdir(UPLOAD_DIR):
            if os.path.splitext(filename)[0] == file_id:
                file_path = os.path.join(UPLOAD_DIR, filename)
                if os.path.exists(file_path):
                    # 创建临时file_info
                    file_extension = os.path.splitext(filename)[1].lower()
                    file_info = {
                        "id": file_id,
                        "original_filename": filename,
                        "filename": filename,
                        "path": file_path,
                        "size": os.path.getsize(file_path),
                        "upload_time": datetime.now().isoformat(),
                        "extension": file_extension[1:],
                        "file_type": "geojson" if file_extension in ALLOWED_GEOJSON_EXTENSIONS else "data"
                    }
                    # 添加到file_db
                    file_db.append(file_info)
                    save_file_db()
                    break
    
    if not file_info:
        raise HTTPException(
            status_code=404,
            detail="文件不存在"
        )
    
    try:
        file_path = file_info["path"]
        
        # 根据文件类型读取
        if file_info["extension"] == "csv":
            df = pd.read_csv(file_path)
        else:  # excel
            df = pd.read_excel(file_path)
        
        # 获取数据信息
        row_count = int(len(df))
        column_count = int(len(df.columns))
        columns = [str(col) for col in df.columns.tolist()]
        
        # 获取数据类型信息，避免JSON序列化错误
        data_types = {}
        for col in df.columns:
            # 安全地获取数据类型
            try:
                data_types[str(col)] = str(df[col].dtype)
            except Exception:
                data_types[str(col)] = "unknown"
        
        # 直接返回简单的字典
        return {
            "success": True,
            "data": {
                "id": str(file_info["id"]),
                "original_filename": str(file_info["original_filename"]),
                "filename": str(file_info["filename"]),
                "size": int(file_info["size"]),
                "upload_time": str(file_info["upload_time"]),
                "extension": str(file_info["extension"]),
                "row_count": row_count,
                "column_count": column_count,
                "columns": columns,
                "data_types": data_types
            }
        }
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"获取文件信息失败: {error_detail}")
        raise HTTPException(
            status_code=500,
            detail=f"获取文件信息失败: {str(e)}"
        )

@router.get("/{file_id}/download", summary="下载文件")
async def download_file(file_id: str):
    """
    下载指定文件
    """
    # 查找文件
    file_info = next((f for f in file_db if f["id"] == file_id), None)
    if not file_info:
        raise HTTPException(
            status_code=404,
            detail="文件不存在"
        )
    
    file_path = file_info["path"]
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="文件已被删除"
        )
    
    return FileResponse(
        path=file_path,
        filename=file_info["original_filename"],
        media_type="application/octet-stream"
    )


@router.post("/batch-download", summary="批量下载文件（打包成zip）")
async def batch_download_files(file_ids: List[str] = Body(..., description="文件ID列表", embed=True)):
    """
    批量下载文件，将多个文件打包成zip文件下载
    """
    if not file_ids or len(file_ids) == 0:
        raise HTTPException(
            status_code=400,
            detail="请提供要下载的文件ID列表"
        )
    
    # 验证所有文件是否存在
    file_infos = []
    for file_id in file_ids:
        file_info = next((f for f in file_db if f["id"] == file_id), None)
        if not file_info:
            raise HTTPException(
                status_code=404,
                detail=f"文件ID {file_id} 不存在"
            )
        if not os.path.exists(file_info["path"]):
            raise HTTPException(
                status_code=404,
                detail=f"文件ID {file_id} 已被删除"
            )
        file_infos.append(file_info)
    
    # 创建临时zip文件
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
        temp_zip_path = temp_zip.name
    
    try:
        # 将文件添加到zip中
        with zipfile.ZipFile(temp_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_info in file_infos:
                # 添加文件到zip，使用原始文件名
                zipf.write(file_info["path"], arcname=file_info["original_filename"])
        
        # 返回zip文件
        return FileResponse(
            path=temp_zip_path,
            filename=f"files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            }
        )
    finally:
        # 确保临时文件被删除
        if os.path.exists(temp_zip_path):
            os.unlink(temp_zip_path)


@router.patch("/{file_id}/rename", summary="修改文件显示名称并可选重命名磁盘文件")
async def rename_file(file_id: str, new_name: str = Query(..., description="新的显示名称/磁盘名（仅文件名，不含路径）")):
    """修改 `original_filename`，并将磁盘文件重命名为相同的名字（保留目录）。

    行为：
    - 验证并清洗 new_name（只使用 basename，禁止路径穿越）
    - 如果 new_name 不含扩展名，保留原始文件扩展名
    - 禁止更改扩展名（避免文件类型不一致）
    - 先在磁盘上重命名文件，再更新内存和持久化；任一步骤失败会回滚。
    """
    # 查找文件
    file_info = next((f for f in file_db if f["id"] == file_id), None)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 校验并清洗新名称
    if not new_name or not isinstance(new_name, str) or new_name.strip() == "":
        raise HTTPException(status_code=400, detail="新的文件名不能为空")

    # 只取 basename，防止路径穿越
    safe_name = os.path.basename(new_name.strip())
    if safe_name == '' or safe_name in ('.', '..'):
        raise HTTPException(status_code=400, detail="无效的文件名")

    # 当前磁盘路径和扩展名
    old_path = file_info.get('path')
    if not old_path or not os.path.exists(old_path):
        raise HTTPException(status_code=404, detail="磁盘文件不存在")

    old_dir = os.path.dirname(old_path)
    old_filename = file_info.get('filename')
    old_ext = os.path.splitext(old_filename)[1]  # 包含点，例如 '.csv'

    # 处理 new name 的扩展名
    new_root, new_ext = os.path.splitext(safe_name)
    if new_ext == '':
        # 未指定扩展名，保留原扩展名
        target_filename = safe_name + old_ext
    else:
        # 指定了扩展名，禁止更改扩展名以避免类型不匹配
        if new_ext.lower() != old_ext.lower():
            raise HTTPException(status_code=400, detail=f"不允许更改文件扩展名（要求: {old_ext}）")
        target_filename = safe_name

    target_path = os.path.join(old_dir, target_filename)
    # 计划中的新ID（与文件名根一致）
    planned_new_id = os.path.splitext(target_filename)[0]

    # 如果目标路径已存在且不是当前文件，拒绝操作
    if os.path.exists(target_path) and os.path.abspath(target_path) != os.path.abspath(old_path):
        raise HTTPException(status_code=400, detail="目标文件名已存在，请选择其他名称")

    # 现在执行磁盘重命名，再持久化 file_db；如遇错误进行回滚
    try:
        # 如果目标和原始相同（路径相同），只更新 original_filename 并持久化，不变更 id
        if os.path.abspath(target_path) == os.path.abspath(old_path):
            prev_original = file_info.get('original_filename')
            file_info['original_filename'] = safe_name
            try:
                save_file_db()
            except Exception as e:
                file_info['original_filename'] = prev_original
                raise HTTPException(status_code=500, detail=f"持久化失败: {str(e)}")
            return make_json_serializable({"success": True, "message": "文件显示名已更新", "data": file_info})

        # 检查即将生效的新ID是否与其他记录冲突
        if any(f is not file_info and f.get('id') == planned_new_id for f in file_db):
            raise HTTPException(status_code=400, detail="目标文件名对应的ID已存在，请更换名称")

        # 执行磁盘重命名
        os.rename(old_path, target_path)
        # 记录旧值以便回滚
        prev_filename = file_info.get('filename')
        prev_path = file_info.get('path')
        prev_original = file_info.get('original_filename')
        prev_id = file_info.get('id')

        # 更新内存记录（包括ID与文件名根一致）
        file_info['filename'] = target_filename
        file_info['path'] = target_path
        file_info['original_filename'] = safe_name
        file_info['id'] = planned_new_id

        try:
            save_file_db()
        except Exception as e:
            # 尝试回滚磁盘文件名
            try:
                if os.path.exists(target_path) and not os.path.exists(old_path):
                    os.rename(target_path, old_path)
            except Exception:
                # 回滚失败——记录并抛出更严重错误
                raise HTTPException(status_code=500, detail=f"持久化失败且回滚磁盘文件失败: {str(e)}")

            # 回滚内存字段
            file_info['filename'] = prev_filename
            file_info['path'] = prev_path
            file_info['original_filename'] = prev_original
            file_info['id'] = prev_id
            raise HTTPException(status_code=500, detail=f"持久化失败: {str(e)}")

        return make_json_serializable({"success": True, "message": "文件及显示名已更新", "data": file_info})

    except HTTPException:
        raise
    except Exception as e:
        # 一般性磁盘操作失败，尝试提供友好信息
        raise HTTPException(status_code=500, detail=f"重命名文件失败: {str(e)}")





@router.get("/{file_id}/analyze", summary="智能分析文件并推荐配置")
async def analyze_file(file_id: str):
    """
    分析文件内容，返回智能推荐的预处理和异常检测配置
    """
    # 查找文件
    file_info = next((f for f in file_db if f["id"] == file_id), None)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        file_path = file_info["path"]

        # 读取文件
        if file_info["extension"] == "csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        logger.info(f"分析文件: {file_info['filename']}, 形状: {df.shape}")

        # 分析数据特征
        total_rows = len(df)
        total_cols = len(df.columns)

        # 识别列类型
        numeric_cols = []
        datetime_cols = []
        string_cols = []

        for col in df.columns:
            # 检查是否是日期时间列
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                datetime_cols.append(col)
            # 尝试转换为日期时间
            elif df[col].dtype == 'object':
                try:
                    pd.to_datetime(df[col], errors='raise')
                    datetime_cols.append(col)
                except:
                    # 尝试转换为数值
                    try:
                        pd.to_numeric(df[col], errors='raise')
                        numeric_cols.append(col)
                    except:
                        string_cols.append(col)
            # 数值列
            elif pd.api.types.is_numeric_dtype(df[col]):
                numeric_cols.append(col)
            else:
                string_cols.append(col)

        # 计算数据质量指标
        missing_count = df.isnull().sum().sum()
        missing_ratio = missing_count / (total_rows * total_cols) if total_rows * total_cols > 0 else 0

        # 检查重复行
        duplicate_count = df.duplicated().sum()
        duplicate_ratio = duplicate_count / total_rows if total_rows > 0 else 0

        # 检查数值列的异常值（无穷大）
        inf_count = 0
        for col in numeric_cols:
            inf_count += np.isinf(df[col]).sum()

        # 生成预处理推荐
        preprocess_recommendations = {
            "missing_values": {
                "enabled": missing_ratio > 0.01,  # 缺失值超过1%时推荐处理
                "method": "mean" if missing_ratio < 0.3 else "drop",  # 缺失值少用均值填充，多则删除
                "reason": f"检测到 {missing_count} 个缺失值 ({missing_ratio*100:.2f}%)"
            },
            "duplicates": {
                "enabled": duplicate_ratio > 0.01,  # 重复行超过1%时推荐处理
                "reason": f"检测到 {duplicate_count} 个重复行 ({duplicate_ratio*100:.2f}%)"
            },
            "outliers": {
                "enabled": len(numeric_cols) > 0,  # 有数值列时推荐异常值检测
                "method": "iqr",
                "reason": f"数据包含 {len(numeric_cols)} 个数值列，建议检测异常值"
            },
            "normalization": {
                "enabled": len(numeric_cols) > 1,  # 多个数值列时推荐标准化
                "method": "zscore",
                "reason": f"数据包含 {len(numeric_cols)} 个数值列，建议进行标准化"
            }
        }

        # 生成异常检测推荐
        # 根据数据规模选择算法
        if total_rows < 1000:
            recommended_method = "lof"
            method_reason = "数据量较小，推荐使用LOF算法（局部异常因子）"
        elif total_rows < 10000:
            recommended_method = "isolation_forest"
            method_reason = "数据量适中，推荐使用Isolation Forest算法"
        else:
            recommended_method = "one_class_svm"
            method_reason = "数据量较大，推荐使用One-Class SVM算法"

        # 根据数据特征推荐contamination
        if missing_ratio > 0.1 or duplicate_ratio > 0.1:
            recommended_contamination = 0.15
            contamination_reason = "数据质量较低，建议提高异常比例阈值"
        else:
            recommended_contamination = 0.1
            contamination_reason = "数据质量良好，使用标准异常比例阈值"

        anomaly_recommendations = {
            "method": recommended_method,
            "method_reason": method_reason,
            "contamination": recommended_contamination,
            "contamination_reason": contamination_reason,
            "features": numeric_cols,  # 推荐使用所有数值列
            "features_reason": f"自动选择 {len(numeric_cols)} 个数值列进行异常检测"
        }

        # 返回分析结果和推荐
        result = {
            "success": True,
            "data": {
                "file_info": {
                    "total_rows": int(total_rows),
                    "total_cols": int(total_cols),
                    "numeric_cols": len(numeric_cols),
                    "datetime_cols": len(datetime_cols),
                    "string_cols": len(string_cols)
                },
                "data_quality": {
                    "missing_count": int(missing_count),
                    "missing_ratio": float(missing_ratio),
                    "duplicate_count": int(duplicate_count),
                    "duplicate_ratio": float(duplicate_ratio),
                    "inf_count": int(inf_count)
                },
                "column_types": {
                    "numeric": numeric_cols,
                    "datetime": datetime_cols,
                    "string": string_cols
                },
                "preprocess_recommendations": preprocess_recommendations,
                "anomaly_recommendations": anomaly_recommendations
            }
        }

        logger.info(f"文件分析完成: {file_info['filename']}")
        return make_json_serializable(result)

    except Exception as e:
        logger.error(f"文件分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件分析失败: {str(e)}")
