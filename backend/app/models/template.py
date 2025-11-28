"""
模板数据模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.sql import func
from .database import Base


class Template(Base):
    """模板数据模型"""
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)  # 限制长度避免索引过长
    type = Column(String(20), nullable=False, index=True)  # anomaly, cluster, predict
    config = Column(Text, nullable=False)  # JSON格式的配置数据
    results = Column(LONGTEXT, nullable=True)  # 使用LONGTEXT存储大JSON数据，支持更大的数据量（4GB）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
