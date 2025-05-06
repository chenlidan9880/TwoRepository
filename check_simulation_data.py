#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查生成的模拟数据数量
"""

from app import create_app, db
from app.models.device import Device
from app.models.terminal import Terminal
from app.models.traffic import Traffic
from app.models.alert import Alert

def main():
    """检查数据库中的模拟数据数量"""
    app = create_app()
    with app.app_context():
        print("=" * 40)
        print("模拟数据统计")
        print("=" * 40)
        print(f"网络设备数量: {Device.query.count()}")
        print(f"终端设备数量: {Terminal.query.count()}")
        print(f"流量记录数量: {Traffic.query.count()}")
        print(f"安全告警数量: {Alert.query.count()}")
        print("=" * 40)
        
        # 按设备类型统计
        device_types = db.session.query(Device.device_type, db.func.count()).group_by(Device.device_type).all()
        print("\n设备类型统计:")
        for type_name, count in device_types:
            print(f"  - {type_name}: {count}个")
            
        # 按终端类型统计
        terminal_types = db.session.query(Terminal.device_type, db.func.count()).group_by(Terminal.device_type).all()
        print("\n终端类型统计:")
        for type_name, count in terminal_types:
            print(f"  - {type_name}: {count}个")
            
        # 按告警类型统计
        alert_types = db.session.query(Alert.alert_type, db.func.count()).group_by(Alert.alert_type).all()
        print("\n告警类型统计:")
        for type_name, count in alert_types:
            print(f"  - {type_name}: {count}个")
        
        print("\n模拟数据检查完成!")

if __name__ == "__main__":
    main() 