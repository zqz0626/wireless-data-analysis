#!/usr/bin/env python3
"""
测试数据库连接脚本
用于验证后端服务是否能够正常连接到MySQL数据库
"""

import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config.settings import settings


def test_db_connection():
    """测试数据库连接"""
    print("测试数据库连接...")
    print(f"数据库URL: {settings.DATABASE_URL}")
    
    try:
        # 创建数据库引擎
        engine = create_engine(settings.DATABASE_URL)
        
        # 测试连接
        with engine.connect() as connection:
            print("✅ 成功连接到数据库")
            
            # 测试执行SQL查询
            result = connection.execute(text("SELECT 1"))
            for row in result:
                print(f"✅ 成功执行SQL查询: {row}")
        
        # 测试会话创建
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        try:
            # 测试查询模板表
            result = db.execute(text("SELECT COUNT(*) FROM templates"))
            count = result.scalar()
            print(f"✅ 成功查询模板表，共有 {count} 条记录")
        finally:
            db.close()
            print("✅ 成功关闭数据库会话")
        
        print("\n🎉 数据库连接测试全部通过！")
        return True
    
    except Exception as e:
        print(f"❌ 数据库连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_db_connection()
    sys.exit(0 if success else 1)