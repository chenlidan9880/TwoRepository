#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
添加测试数据到校园网监控系统
"""

from app import create_app, db
from app.models.device import Device
from app.models.terminal import Terminal
from datetime import datetime

def add_test_devices():
    """添加测试网络设备"""
    devices = [
        {
            'name': '核心交换机01',
            'ip_address': '192.168.1.1',
            'location': '网络中心机房',
            'device_type': 'switch',
            'description': 'Cisco Catalyst 9600',
            'status': 'active',
            'snmp_community': 'public'
        },
        {
            'name': '接入交换机02',
            'ip_address': '192.168.1.2',
            'location': '计算机学院机房',
            'device_type': 'switch',
            'description': 'Huawei S5700',
            'status': 'active',
            'snmp_community': 'public'
        },
        {
            'name': '边界路由器01',
            'ip_address': '192.168.1.254',
            'location': '网络中心机房',
            'device_type': 'router',
            'description': 'Cisco ASR 9000',
            'status': 'active',
            'snmp_community': 'public'
        },
        {
            'name': '无线控制器01',
            'ip_address': '192.168.2.1',
            'location': '网络中心机房',
            'device_type': 'wireless',
            'description': 'Aruba 7200',
            'status': 'active',
            'snmp_community': 'public'
        }
    ]
    
    for device_data in devices:
        device = Device.query.filter_by(ip_address=device_data['ip_address']).first()
        if not device:
            device = Device(**device_data)
            device.created_at = datetime.now()
            device.updated_at = datetime.now()
            db.session.add(device)
            print(f"添加设备: {device_data['name']}")
        else:
            print(f"设备已存在: {device_data['name']}")
    
    db.session.commit()
    print(f"设备添加完成，当前设备总数: {Device.query.count()}")

def add_test_terminals():
    """添加测试终端设备"""
    # 获取设备ID
    devices = Device.query.all()
    if not devices:
        print("没有可用的网络设备，跳过终端添加")
        return
    
    device_ids = [device.id for device in devices]
    
    terminals = [
        {
            'hostname': 'student-pc1',
            'mac_address': '00:1A:2B:3C:4D:5E',
            'ip_address': '192.168.10.101',
            'device_type': 'PC',
            'os_type': 'Windows',
            'vendor': 'Dell',
            'connected_device_id': device_ids[0] if len(device_ids) > 0 else None,
            'status': 'online',
            'location': '计算机学院机房'
        },
        {
            'hostname': 'teacher-laptop1',
            'mac_address': '00:1A:2B:3C:4D:6F',
            'ip_address': '192.168.10.102',
            'device_type': 'PC',
            'os_type': 'macOS',
            'vendor': 'Apple',
            'connected_device_id': device_ids[0] if len(device_ids) > 0 else None,
            'status': 'online',
            'location': '教师办公室'
        },
        {
            'hostname': 'student-phone1',
            'mac_address': '00:1A:2B:3C:4D:7G',
            'ip_address': '192.168.20.103',
            'device_type': 'Mobile',
            'os_type': 'Android',
            'vendor': 'Samsung',
            'connected_device_id': device_ids[1] if len(device_ids) > 1 else None,
            'status': 'online',
            'location': '学生宿舍'
        },
        {
            'hostname': 'library-pc1',
            'mac_address': '00:1A:2B:3C:4D:8H',
            'ip_address': '192.168.30.104',
            'device_type': 'PC',
            'os_type': 'Linux',
            'vendor': 'Lenovo',
            'connected_device_id': device_ids[1] if len(device_ids) > 1 else None,
            'status': 'online',
            'location': '图书馆'
        }
    ]
    
    for terminal_data in terminals:
        terminal = Terminal.query.filter_by(mac_address=terminal_data['mac_address']).first()
        if not terminal:
            terminal = Terminal(**terminal_data)
            terminal.created_at = datetime.now()
            terminal.updated_at = datetime.now()
            terminal.last_seen = datetime.now()
            terminal.is_active = True
            db.session.add(terminal)
            print(f"添加终端: {terminal_data['hostname']}")
        else:
            print(f"终端已存在: {terminal_data['hostname']}")
    
    db.session.commit()
    print(f"终端添加完成，当前终端总数: {Terminal.query.count()}")

def main():
    """主函数"""
    app = create_app()
    with app.app_context():
        print("开始添加测试数据...")
        add_test_devices()
        add_test_terminals()
        print("测试数据添加完成！")

if __name__ == "__main__":
    main() 