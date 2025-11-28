"""
项目配置管理 - 统一管理所有配置项
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""
    
    # 基础配置
    APP_NAME: str = "无线大数据分析系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    
    # 文件上传配置
    UPLOAD_DIR: Path = Path("uploads")
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: list = ["csv", "xlsx", "xls"]
    
    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/wireless-data-analysis?charset=utf8mb4"
    
    # 机器学习配置
    MAX_CATEGORIES_FOR_ONE_HOT: int = 50  # 独热编码最大类别数
    DEFAULT_CONTAMINATION: float = 0.1  # 默认异常检测比例
    MAX_SAMPLES_FOR_ANOMALY: int = 10000  # 异常检测最大样本数
    
    # 缓存配置
    CACHE_TTL: int = 300  # 缓存时间（秒）
    
    # 安全配置
    CORS_ORIGINS: list = ["*"]  # 生产环境应限制具体域名
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 创建全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings


def update_settings(new_settings: Dict[str, Any]) -> None:
    """更新配置（主要用于测试）"""
    for key, value in new_settings.items():
        if hasattr(settings, key):
            setattr(settings, key, value)


# 配置验证函数
def validate_config() -> bool:
    """验证配置是否有效"""
    try:
        # 验证上传目录
        settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # 验证文件大小限制
        if settings.MAX_FILE_SIZE <= 0:
            raise ValueError("MAX_FILE_SIZE 必须大于0")
            
        # 验证异常检测参数
        if not (0 < settings.DEFAULT_CONTAMINATION < 1):
            raise ValueError("DEFAULT_CONTAMINATION 必须在0和1之间")
            
        return True
    except Exception as e:
        print(f"配置验证失败: {e}")
        return False


# 配置信息获取函数
def get_config_info() -> Dict[str, Any]:
    """获取配置信息摘要"""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "host": settings.HOST,
        "port": settings.PORT,
        "upload_dir": str(settings.UPLOAD_DIR),
        "max_file_size": settings.MAX_FILE_SIZE,
        "allowed_extensions": settings.ALLOWED_EXTENSIONS,
    }


def ensure_upload_dir() -> None:
    """确保上传目录存在"""
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)