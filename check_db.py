#!/usr/bin/env python3
"""
检查数据库中是否有模板数据
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加backend目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# 从settings.py获取数据库配置
from app.config.settings import settings

# 创建数据库引擎
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_templates_data():
    """检查templates表中是否有数据"""
    db = SessionLocal()
    try:
        print("正在连接数据库...")
        
        # 查询templates表中的记录数量
        count = db.execute(text("SELECT COUNT(*) FROM templates")).scalar()
        print(f"templates表中共有 {count} 条记录")
        
        # 如果有记录，查询前5条记录的基本信息
        if count > 0:
            print("\n前5条记录信息：")
            templates = db.execute(text("SELECT id, name, type, created_at FROM templates ORDER BY created_at DESC LIMIT 5")).fetchall()
            for template in templates:
                print(f"ID: {template.id}, 名称: {template.name}, 类型: {template.type}, 创建时间: {template.created_at}")
        
        return count
    except Exception as e:
        print(f"查询数据库失败: {e}")
        return 0
    finally:
        db.close()

if __name__ == "__main__":
    check_templates_data()
