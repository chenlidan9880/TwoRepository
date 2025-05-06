"""
修复数据库，添加终端设备表的vendor和user_agent字段
"""

import pymysql
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库连接参数
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 3306))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'campus_network')

def fix_database():
    try:
        # 连接到数据库
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        
        cursor = conn.cursor()
        
        # 检查vendor字段是否存在
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'terminals' 
            AND column_name = 'vendor'
        """)
        vendor_exists = cursor.fetchone()[0] > 0
        
        # 检查user_agent字段是否存在
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'terminals' 
            AND column_name = 'user_agent'
        """)
        user_agent_exists = cursor.fetchone()[0] > 0
        
        # 添加缺少的字段
        if not vendor_exists:
            cursor.execute("ALTER TABLE terminals ADD COLUMN vendor VARCHAR(64)")
            print("成功添加vendor字段")
        else:
            print("vendor字段已存在，跳过添加")
            
        if not user_agent_exists:
            cursor.execute("ALTER TABLE terminals ADD COLUMN user_agent TEXT")
            print("成功添加user_agent字段")
        else:
            print("user_agent字段已存在，跳过添加")
        
        # 提交更改
        conn.commit()
        print("数据库修复完成")
        
    except Exception as e:
        print(f"数据库操作失败: {e}")
    finally:
        # 关闭连接
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    fix_database() 