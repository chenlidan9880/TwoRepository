"""
重置数据库并重建示例数据的脚本

使用方法: python reset_db.py
"""

import os
from app import create_app, db
from app.models.user import User
from app.models.device import Device
from app.models.traffic import Traffic
from app.models.alert import Alert
from app.models.terminal import Terminal
from init_sample_data import init_sample_data

def reset_database():
    """重置数据库并重建示例数据"""
    print("开始重置数据库...")
    
    # 创建 Flask 应用上下文
    app = create_app('development')
    
    with app.app_context():
        # 删除所有表并重新创建
        print("删除现有表...")
        db.drop_all()
        print("创建新表...")
        db.create_all()
        
        # 初始化示例数据
        print("初始化示例数据...")
        try:
            init_sample_data()
            print("数据库重置完成!")
        except Exception as e:
            print(f"初始化示例数据失败: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    reset_database() 