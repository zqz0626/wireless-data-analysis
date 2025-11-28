"""
数据库连接和会话管理
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config.settings import settings

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,  # 增加连接池大小
    max_overflow=40,  # 增加最大溢出连接数
    pool_timeout=60,  # 增加获取连接的超时时间（秒）
    pool_recycle=3600,  # 连接回收时间（秒）
    pool_pre_ping=True  # 连接使用前检查，确保连接有效
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
