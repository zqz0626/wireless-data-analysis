#!/usr/bin/env python3
"""
检查数据库表结构脚本
用于查看templates表的结构，特别是results列的类型
"""

import sys
from sqlalchemy import create_engine, inspect
from app.config.settings import settings


def check_table_structure():
    """检查数据库表结构"""
    print("检查数据库表结构...")
    print(f"数据库URL: {settings.DATABASE_URL}")
    
    try:
        # 创建数据库引擎
        engine = create_engine(settings.DATABASE_URL)
        
        # 创建inspector对象
        inspector = inspect(engine)
        
        # 获取templates表的结构
        table_name = 'templates'
        if table_name in inspector.get_table_names():
            print(f"\n✅ 找到了表: {table_name}")
            
            # 获取表的列信息
            columns = inspector.get_columns(table_name)
            print("\n表结构信息:")
            for column in columns:
                print(f"  - {column['name']}: {column['type']} (nullable: {column['nullable']})")
            
            # 获取表的索引信息
            indexes = inspector.get_indexes(table_name)
            if indexes:
                print("\n索引信息:")
                for index in indexes:
                    print(f"  - {index['name']}: {index['column_names']} (unique: {index['unique']})")
            
            # 获取表的约束信息
            constraints = inspector.get_check_constraints(table_name)
            if constraints:
                print("\n约束信息:")
                for constraint in constraints:
                    print(f"  - {constraint['name']}: {constraint['sqltext']}")
            
            return True
        else:
            print(f"❌ 未找到表: {table_name}")
            return False
    
    except Exception as e:
        print(f"❌ 检查表结构失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = check_table_structure()
    sys.exit(0 if success else 1)