"""
API 路由包
负责注册和管理所有后端 API 路由
包含文件管理、数据预处理、数据分析和预测分析相关的接口路由
"""

from fastapi import APIRouter
from .file_router import router as file_router        # 文件管理路由
from .preprocess_router import router as preprocess_router  # 数据预处理路由
from .analysis_router import router as analysis_router    # 数据分析路由
from .predict_router import router as predict_router      # 预测分析路由
from .template_router import router as template_router    # 模板管理路由

"""
创建主 API 路由实例
- prefix: 路由前缀，所有子路由都会继承此前缀
"""
api_router = APIRouter(prefix="/api")

"""
注册子路由
将各个功能模块的路由注册到主路由中
- router: 子路由实例
- prefix: 子路由前缀
- tags: 路由标签，用于 API 文档分组
"""
api_router.include_router(file_router, prefix="/files", tags=["files"])          # 注册文件管理路由
api_router.include_router(preprocess_router, prefix="/preprocess", tags=["preprocess"])  # 注册数据预处理路由
api_router.include_router(analysis_router, prefix="/analysis", tags=["analysis"])    # 注册数据分析路由
api_router.include_router(predict_router, prefix="/predict", tags=["predict"])      # 注册预测分析路由
api_router.include_router(template_router)  # 注册模板管理路由，已在template_router中设置prefix

"""
导出主 API 路由
用于在 main.py 中注册到 FastAPI 应用
"""
__all__ = ["api_router"]
