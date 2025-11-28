#!/usr/bin/env python3
"""
更新数据库表结构脚本
用于删除templates表中的updated_at列
"""

import sys
from sqlalchemy import create_engine, text
from app.config.settings import settings


def update_table_structure():
    """更新数据库表结构"""
    print("更新数据库表结构...")
    print(f"数据库URL: {settings.DATABASE_URL}")
    
    try:
        # 创建数据库引擎
        engine = create_engine(settings.DATABASE_URL)
        
        # 连接数据库
        with engine.connect() as connection:
            # 开始事务
            trans = connection.begin()
            
            try:
                # 删除updated_at列
                alter_table_sql = text("ALTER TABLE templates DROP COLUMN updated_at")
                connection.execute(alter_table_sql)
                print("✅ 成功删除updated_at列")
                
                # 提交事务
                trans.commit()
                print("✅ 事务提交成功")
                
                # 验证修改结果
                check_sql = text("DESCRIBE templates")
                result = connection.execute(check_sql)
                print("\n修改后的表结构:")
                for row in result:
                    print(f"  - {row[0]}: {row[1]} (nullable: {row[2]})")
                
                return True
            except Exception as e:
                # 回滚事务
                trans.rollback()
                print(f"❌ 执行SQL失败，事务已回滚: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    except Exception as e:
        print(f"❌ 更新表结构失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = update_table_structure()
    sys.exit(0 if success else 1)