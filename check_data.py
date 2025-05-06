#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查数据库中的数据
"""

from app import create_app, db
from app.models.device import Device
from app.models.terminal import Terminal
from app.models.traffic import Traffic
import sys

def check_data():
    """检查数据库中的数据"""
    app = create_app()
    with app.app_context():
        print("数据库检查结果:")
        print("-" * 40)
        
        # 检查设备数据
        devices = Device.query.all()
        print(f"设备数量: {len(devices)}")
        if devices:
            print("设备列表:")
            for device in devices:
                print(f"  - {device.name} ({device.ip_address}), 状态: {device.status}")
        
        print("-" * 40)
        
        # 检查终端数据
        terminals = Terminal.query.all()
        print(f"终端数量: {len(terminals)}")
        if terminals:
            print("终端列表:")
            for terminal in terminals[:5]:  # 只显示前5个终端
                print(f"  - {terminal.hostname} ({terminal.ip_address}), 状态: {terminal.status}")
            if len(terminals) > 5:
                print(f"  ...以及其他 {len(terminals)-5} 个终端")
        
        print("-" * 40)
        
        # 检查流量数据
        traffic_data = Traffic.query.all()
        print(f"流量数据条数: {len(traffic_data)}")
        if traffic_data:
            print("最近5条流量数据:")
            for traffic in traffic_data[-5:]:  # 只显示最近5条
                device = Device.query.get(traffic.device_id)
                device_name = device.name if device else "未知设备"
                print(f"  - 设备: {device_name}, 时间: {traffic.timestamp}, 入站: {traffic.in_octets}, 出站: {traffic.out_octets}")
        
        print("-" * 40)
        print("数据库检查完成")

if __name__ == "__main__":
    try:
        check_data()
    except Exception as e:
        print(f"检查数据时出错: {str(e)}")
        sys.exit(1) 