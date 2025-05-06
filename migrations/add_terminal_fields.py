"""
数据库迁移脚本：添加终端设备表的vendor和user_agent字段
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app import app, db
from flask_migrate import Migrate, upgrade
from sqlalchemy import Column, String, Text

def alter_terminals_table():
    """
    修改terminals表，添加vendor和user_agent字段
    """
    with app.app_context():
        try:
            # 尝试直接执行ALTER TABLE语句
            db.session.execute("ALTER TABLE terminals ADD COLUMN IF NOT EXISTS vendor VARCHAR(64)")
            db.session.execute("ALTER TABLE terminals ADD COLUMN IF NOT EXISTS user_agent TEXT")
            db.session.commit()
            print("成功添加terminals表的vendor和user_agent字段")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"添加字段失败: {str(e)}")
            return False

if __name__ == "__main__":
    # 创建迁移对象
    migrate = Migrate(app, db)
    
    # 执行字段添加
    alter_terminals_table() 