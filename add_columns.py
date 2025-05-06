"""
直接执行SQL添加terminals表的vendor和user_agent字段
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

def column_exists(cursor, table_name, column_name):
    """检查列是否已存在"""
    cursor.execute(f"""
        SELECT COUNT(*) FROM information_schema.columns 
        WHERE table_schema = DATABASE() 
        AND table_name = '{table_name}' 
        AND column_name = '{column_name}'
    """)
    return cursor.fetchone()[0] > 0

def add_columns():
    """直接执行SQL添加字段"""
    try:
        # 连接到数据库
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )

        with conn.cursor() as cursor:
            # 检查并添加vendor字段
            if not column_exists(cursor, 'terminals', 'vendor'):
                try:
                    cursor.execute("ALTER TABLE terminals ADD COLUMN vendor VARCHAR(64)")
                    print("成功添加vendor字段")
                except Exception as e:
                    print(f"添加vendor字段失败: {e}")
            else:
                print("vendor字段已存在，跳过添加")

            # 检查并添加user_agent字段
            if not column_exists(cursor, 'terminals', 'user_agent'):
                try:
                    cursor.execute("ALTER TABLE terminals ADD COLUMN user_agent TEXT")
                    print("成功添加user_agent字段")
                except Exception as e:
                    print(f"添加user_agent字段失败: {e}")
            else:
                print("user_agent字段已存在，跳过添加")

            # 提交更改
            conn.commit()
            print("字段添加完成")

    except Exception as e:
        print(f"数据库连接或操作失败: {e}")
    finally:
        # 关闭连接
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    add_columns()