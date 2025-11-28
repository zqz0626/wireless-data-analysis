"""
Wireless Analytics Backend Application Package
"""
from .config.settings import settings, ensure_upload_dir

__version__ = settings.APP_VERSION

# 初始化应用时确保上传目录存在
def initialize_app() -> None:
    """初始化应用"""
    ensure_upload_dir()
