"""
异常处理中间件 - 统一处理所有异常
"""

import logging
import traceback
from typing import Dict, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class CustomException(Exception):
    """自定义异常基类"""
    
    def __init__(self, message: str, code: str = "CUSTOM_ERROR", status_code: int = 500, details: Any = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class FileProcessingError(CustomException):
    """文件处理异常"""
    
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, "FILE_PROCESSING_ERROR", 400, details)


class DataValidationError(CustomException):
    """数据验证异常"""
    
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, "DATA_VALIDATION_ERROR", 400, details)


class ModelTrainingError(CustomException):
    """模型训练异常"""
    
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, "MODEL_TRAINING_ERROR", 500, details)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局异常处理器"""
    
    # 记录错误日志
    logger.error(f"请求异常: {request.method} {request.url}")
    logger.error(f"异常类型: {type(exc).__name__}")
    logger.error(f"异常信息: {str(exc)}")
    logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")
    
    # 根据异常类型返回不同的响应
    if isinstance(exc, CustomException):
        # 自定义异常
        response_data = {
            "success": False,
            "error": exc.code,
            "message": exc.message,
            "details": exc.details
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=response_data
        )
    
    elif isinstance(exc, RequestValidationError):
        # 请求验证错误
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        response_data = {
            "success": False,
            "error": "VALIDATION_ERROR",
            "message": "请求参数验证失败",
            "details": errors
        }
        return JSONResponse(
            status_code=422,
            content=response_data
        )
    
    elif isinstance(exc, (HTTPException, StarletteHTTPException)):
        # HTTP异常
        response_data = {
            "success": False,
            "error": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "details": None
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=response_data
        )
    
    else:
        # 其他未处理异常
        response_data = {
            "success": False,
            "error": "INTERNAL_SERVER_ERROR",
            "message": "服务器内部错误",
            "details": None
        }
        
        # 生产环境不返回详细错误信息
        if not request.app.debug:
            response_data["message"] = "服务器内部错误，请稍后重试"
        
        return JSONResponse(
            status_code=500,
            content=response_data
        )


def setup_exception_handlers(app):
    """设置异常处理器"""
    
    # 注册全局异常处理器
    app.add_exception_handler(CustomException, global_exception_handler)
    app.add_exception_handler(RequestValidationError, global_exception_handler)
    app.add_exception_handler(HTTPException, global_exception_handler)
    app.add_exception_handler(StarletteHTTPException, global_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
    
    logger.info("异常处理器设置完成")


# 工具函数
def create_error_response(
    error_code: str,
    message: str,
    status_code: int = 400,
    details: Any = None
) -> Dict[str, Any]:
    """创建标准错误响应"""
    return {
        "success": False,
        "error": error_code,
        "message": message,
        "details": details
    }


def handle_file_error(error: Exception, file_path: str = None) -> CustomException:
    """处理文件相关错误"""
    if isinstance(error, FileNotFoundError):
        return FileProcessingError(f"文件不存在: {file_path}")
    elif isinstance(error, PermissionError):
        return FileProcessingError(f"文件权限不足: {file_path}")
    else:
        return FileProcessingError(f"文件处理失败: {str(error)}")


def handle_data_error(error: Exception, operation: str = None) -> CustomException:
    """处理数据相关错误"""
    if operation:
        return DataValidationError(f"{operation} 操作失败: {str(error)}")
    else:
        return DataValidationError(f"数据处理失败: {str(error)}")