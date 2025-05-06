#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
清理数据库依赖关系，解决外键约束问题
"""

from app import create_app, db
from app.models.alert import Alert
from app.models.traffic import Traffic
from app.models.terminal import Terminal


def clear_all_dependencies():
    """清理所有依赖关系数据"""
    app = create_app()
    with app.app_context():
        print("开始清理数据库依赖关系...")

        # 1. 清理告警数据
        try:
            print("删除告警数据...")
            Alert.query.delete()
            db.session.commit()
            print("告警数据删除成功")
        except Exception as e:
            print(f"删除告警数据出错: {str(e)}")
            db.session.rollback()

        # 2. 清理流量数据
        try:
            print("删除流量数据...")
            Traffic.query.delete()
            db.session.commit()
            print("流量数据删除成功")
        except Exception as e:
            print(f"删除流量数据出错: {str(e)}")
            db.session.rollback()

        # 3. 清理终端数据
        try:
            print("删除终端数据...")
            Terminal.query.delete()
            db.session.commit()
            print("终端数据删除成功")
        except Exception as e:
            print(f"删除终端数据出错: {str(e)}")
            db.session.rollback()

        # 不删除设备数据，由主脚本处理
        print("依赖关系清理完成，现在可以安全运行network_topology_generator.py")


if __name__ == "__main__":
    clear_all_dependencies()