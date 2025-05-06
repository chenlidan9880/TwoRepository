#!/usr/bin/env python
"""
数据库初始化脚本
用于创建数据库表结构并添加初始数据
"""

import os
import sys
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models.user import User
from app.models.device import Device
from app.models.terminal import Terminal
from app.models.alert import Alert
from app.models.traffic import Traffic
from app.models.settings import Settings

def create_tables():
    """创建数据库表"""
    print("正在创建数据库表...")
    db.create_all()
    print("数据库表创建完成")

def add_default_user():
    """添加默认管理员用户"""
    print("正在添加默认管理员用户...")
    admin = User.query.filter_by(username='admin').first()
    if admin is None:
        admin = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.session.add(admin)
        db.session.commit()
        print("默认管理员用户添加成功，用户名: admin，密码: admin123")
    else:
        print("默认管理员用户已存在，跳过")

def add_default_settings():
    """添加默认系统设置"""
    print("正在添加默认系统设置...")
    settings = [
        {
            'key': 'traffic_high_threshold',
            'value': '80',
            'type': 'float',
            'description': '流量高负载阈值(%)'
        },
        {
            'key': 'cpu_high_threshold',
            'value': '85',
            'type': 'float',
            'description': 'CPU高负载阈值(%)'
        },
        {
            'key': 'memory_high_threshold',
            'value': '80',
            'type': 'float',
            'description': '内存高负载阈值(%)'
        },
        {
            'key': 'data_retention_days',
            'value': '90',
            'type': 'integer',
            'description': '数据保留天数'
        },
        {
            'key': 'auto_refresh_interval',
            'value': '30',
            'type': 'integer',
            'description': '页面自动刷新间隔(秒)'
        }
    ]
    
    for setting in settings:
        s = Settings.query.filter_by(key=setting['key']).first()
        if s is None:
            s = Settings(
                key=setting['key'],
                value=setting['value'],
                type=setting['type'],
                description=setting['description'],
                updated_at=datetime.now()
            )
            db.session.add(s)
    
    db.session.commit()
    print("默认系统设置添加成功")

def add_sample_data():
    """添加示例数据（可选）"""
    if input("是否添加示例数据？(y/n) ").lower() == 'y':
        print("正在添加示例数据...")
        
        # 添加示例设备
        devices = [
            {
                'name': '核心路由器',
                'ip_address': '192.168.1.1',
                'device_type': '路由器',
                'location': '数据中心',
                'description': '核心路由设备，负责校园网络的路由和转发',
                'status': 'online'
            },
            {
                'name': '主楼交换机',
                'ip_address': '192.168.1.2',
                'device_type': '交换机',
                'location': '主教学楼',
                'description': '主教学楼交换设备，负责主教学楼的网络接入',
                'status': 'online'
            },
            {
                'name': '图书馆交换机',
                'ip_address': '192.168.1.3',
                'device_type': '交换机',
                'location': '图书馆',
                'description': '图书馆交换设备，负责图书馆的网络接入',
                'status': 'online'
            },
            {
                'name': '学生宿舍交换机',
                'ip_address': '192.168.1.4',
                'device_type': '交换机',
                'location': '学生宿舍',
                'description': '学生宿舍交换设备，负责学生宿舍的网络接入',
                'status': 'offline'
            }
        ]
        
        device_objs = []
        for device in devices:
            d = Device.query.filter_by(ip_address=device['ip_address']).first()
            if d is None:
                d = Device(
                    name=device['name'],
                    ip_address=device['ip_address'],
                    device_type=device['device_type'],
                    location=device['location'],
                    description=device['description'],
                    status=device['status'],
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.session.add(d)
                device_objs.append(d)
        
        db.session.commit()
        
        # 添加示例终端
        terminals = [
            {
                'hostname': 'student-pc-001',
                'ip_address': '192.168.10.1',
                'mac_address': '00:1A:2B:3C:4D:5E',
                'device_type': '个人电脑',
                'os_type': 'Windows',
                'status': 'online',
                'location': '学生宿舍'
            },
            {
                'hostname': 'teacher-laptop-001',
                'ip_address': '192.168.20.1',
                'mac_address': '00:1A:2B:3C:4D:5F',
                'device_type': '笔记本电脑',
                'os_type': 'MacOS',
                'status': 'online',
                'location': '教师办公室'
            },
            {
                'hostname': 'lab-pc-001',
                'ip_address': '192.168.30.1',
                'mac_address': '00:1A:2B:3C:4D:60',
                'device_type': '个人电脑',
                'os_type': 'Linux',
                'status': 'offline',
                'location': '计算机实验室'
            }
        ]
        
        for terminal in terminals:
            t = Terminal.query.filter_by(ip_address=terminal['ip_address']).first()
            if t is None:
                t = Terminal(
                    hostname=terminal['hostname'],
                    ip_address=terminal['ip_address'],
                    mac_address=terminal['mac_address'],
                    device_type=terminal['device_type'],
                    os_type=terminal['os_type'],
                    is_active=terminal['status'] == 'online',
                    location=terminal['location'],
                    first_seen=datetime.now() - timedelta(days=7),
                    last_seen=datetime.now() if terminal['status'] == 'online' else datetime.now() - timedelta(days=1),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.session.add(t)
        
        # 添加示例告警
        if device_objs:
            alerts = [
                {
                    'device': device_objs[0],
                    'alert_type': 'cpu_high',
                    'severity': 'warning',
                    'title': 'CPU使用率过高',
                    'message': f"设备 {device_objs[0].name} 的CPU使用率达到90%，超过阈值85%",
                    'value': 90,
                    'threshold': 85,
                    'unit': '%',
                    'is_read': True,
                    'is_handled': False
                },
                {
                    'device': device_objs[1],
                    'alert_type': 'traffic_high',
                    'severity': 'critical',
                    'title': '流量负载过高',
                    'message': f"设备 {device_objs[1].name} 的流量负载达到95%，超过阈值80%",
                    'value': 95,
                    'threshold': 80,
                    'unit': '%',
                    'is_read': False,
                    'is_handled': False
                },
                {
                    'device': device_objs[3],
                    'alert_type': 'device_down',
                    'severity': 'critical',
                    'title': '设备离线',
                    'message': f"设备 {device_objs[3].name} 无法连接，可能已经离线",
                    'is_read': True,
                    'is_handled': True,
                    'handled_at': datetime.now() - timedelta(hours=2)
                }
            ]
            
            for alert in alerts:
                a = Alert(
                    device_id=alert['device'].id,
                    alert_type=alert['alert_type'],
                    severity=alert['severity'],
                    title=alert['title'],
                    message=alert['message'],
                    value=alert.get('value'),
                    threshold=alert.get('threshold'),
                    unit=alert.get('unit'),
                    is_read=alert['is_read'],
                    is_handled=alert['is_handled'],
                    handled_at=alert.get('handled_at'),
                    created_at=datetime.now() - timedelta(hours=4)
                )
                db.session.add(a)
            
            # 添加示例流量数据
            now = datetime.now()
            for device in device_objs:
                for i in range(24):  # 过去24小时的数据
                    time_point = now - timedelta(hours=i)
                    # 模拟两个接口的流量数据
                    for interface in ['GigabitEthernet0/0', 'GigabitEthernet0/1']:
                        # 模拟流量数据，不同时间点有所波动
                        inbound = 1000000 + (i % 12) * 500000
                        outbound = 800000 + (i % 12) * 400000
                        utilization = ((inbound + outbound) / 1000000000) * 100  # 假设1Gbps带宽
                        
                        t = Traffic(
                            device_id=device.id,
                            interface=interface,
                            interface_index=f"{interface.replace('GigabitEthernet', '')}" if 'GigabitEthernet' in interface else '0',
                            inbound=inbound,
                            outbound=outbound,
                            bandwidth_utilization=utilization,
                            timestamp=time_point
                        )
                        db.session.add(t)
        
        db.session.commit()
        print("示例数据添加成功")

def init_db():
    """初始化数据库"""
    create_tables()
    add_default_user()
    add_default_settings()
    add_sample_data()
    print("数据库初始化完成")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        init_db() 