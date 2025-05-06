import os
import random
from datetime import datetime, timedelta
from flask import Flask
from app import create_app, db
from app.models.user import User
from app.models.device import Device
from app.models.traffic import Traffic
from app.models.alert import Alert
from app.models.terminal import Terminal

def init_sample_data():
    """初始化示例数据"""
    print("开始初始化示例数据...")
    
    # 创建管理员用户
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@example.com',
            name='系统管理员',
            department='网络信息中心',
            is_admin=True,
            is_active=True
        )
        admin.set_password('admin')
        db.session.add(admin)
        print("创建管理员用户")
    
    # 创建普通用户
    if not User.query.filter_by(username='user').first():
        user = User(
            username='user',
            email='user@example.com',
            name='测试用户',
            department='测试部门',
            is_admin=False,
            is_active=True
        )
        user.set_password('password')
        db.session.add(user)
        print("创建普通用户")
    
    # 创建网络管理员
    if not User.query.filter_by(username='netadmin').first():
        netadmin = User(
            username='netadmin',
            email='netadmin@example.com',
            name='网络管理员',
            department='网络运维部',
            is_admin=True,
            is_active=True
        )
        netadmin.set_password('netadmin')
        db.session.add(netadmin)
        print("创建网络管理员用户")
    
    # 创建网络设备
    device_list = [
        {'name': '核心交换机', 'ip_address': '192.168.1.1', 'location': '网络中心', 'description': 'Cisco Catalyst 9600', 'device_type': '交换机'},
        {'name': '边缘路由器', 'ip_address': '192.168.1.2', 'location': '网络中心', 'description': 'Cisco ISR 4451', 'device_type': '路由器'},
        {'name': '教学楼交换机', 'ip_address': '192.168.2.1', 'location': '教学楼', 'description': 'Huawei S5700', 'device_type': '交换机'},
        {'name': '实验室交换机', 'ip_address': '192.168.3.1', 'location': '实验室', 'description': 'H3C S5560', 'device_type': '交换机'},
        {'name': '宿舍楼交换机', 'ip_address': '192.168.4.1', 'location': '宿舍楼', 'description': 'TP-Link T2600G', 'device_type': '交换机'},
        {'name': '图书馆无线AP', 'ip_address': '192.168.5.1', 'location': '图书馆', 'description': 'Cisco Aironet 1830', 'device_type': '无线AP'},
    ]
    
    for device_data in device_list:
        if not Device.query.filter_by(ip_address=device_data['ip_address']).first():
            device = Device(
                name=device_data['name'],
                ip_address=device_data['ip_address'],
                location=device_data['location'],
                description=device_data['description'],
                device_type=device_data['device_type'],
                status='online',
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.session.add(device)
            print(f"创建设备: {device_data['name']}")
    
    # 提交设备数据
    db.session.commit()
    
    # 获取所有设备，为它们创建流量数据
    devices = Device.query.all()
    
    # 生成过去24小时的流量数据，每小时一条
    now = datetime.now()
    for device in devices:
        # 删除之前的流量数据
        Traffic.query.filter_by(device_id=device.id).delete()
        
        # 为每个设备分配一些接口
        interfaces = ['GigabitEthernet0/0', 'GigabitEthernet0/1', 'GigabitEthernet0/2']
        
        for interface in interfaces:
            # 设置接口带宽（Gbps）
            bandwidth = 1000000000  # 1Gbps
            
            # 随机生成接口每小时的流量数据
            for hour in range(24, 0, -1):
                time_point = now - timedelta(hours=hour)
                
                # 模拟流量数据，随机生成入站和出站流量
                # 入站字节数（每秒）
                in_octets_per_second = int(random.uniform(10000000, 100000000))  # 10-100 MB/s
                # 出站字节数（每秒）
                out_octets_per_second = int(random.uniform(5000000, 80000000))   # 5-80 MB/s
                
                # 为高峰时段(9-12, 14-17)增加流量
                hour_of_day = time_point.hour
                if (9 <= hour_of_day <= 12) or (14 <= hour_of_day <= 17):
                    in_octets_per_second = int(in_octets_per_second * 1.5)
                    out_octets_per_second = int(out_octets_per_second * 1.5)
                
                # 计算每秒包数（假设平均每个包1000字节）
                in_packets_per_second = in_octets_per_second // 1000
                out_packets_per_second = out_octets_per_second // 1000
                
                # 计算带宽利用率
                utilization = ((in_octets_per_second + out_octets_per_second) * 8 / bandwidth) * 100
                
                # 生成少量的错误
                in_errors = random.randint(0, 10) if random.random() < 0.2 else 0
                out_errors = random.randint(0, 5) if random.random() < 0.1 else 0
                
                # 存储一小时的累计数据
                traffic = Traffic(
                    device_id=device.id,
                    interface=interface,
                    in_octets=in_octets_per_second * 3600,  # 一小时的累计字节数
                    out_octets=out_octets_per_second * 3600,
                    in_packets=in_packets_per_second * 3600,
                    out_packets=out_packets_per_second * 3600,
                    in_errors=in_errors,
                    out_errors=out_errors,
                    bandwidth=bandwidth,
                    utilization=utilization,
                    timestamp=time_point
                )
                db.session.add(traffic)
            
    print("创建流量数据")
    
    # 生成告警数据
    alert_types_map = {
        '流量告警': 'traffic_high',
        'CPU告警': 'cpu_high',
        '内存告警': 'memory_high',
        '设备离线': 'device_down',
        '安全告警': 'security_threat'
    }
    severity_map = {
        '低': 'info',
        '中': 'warning',
        '高': 'critical',
        '紧急': 'critical'
    }
    
    # 清除之前的告警
    Alert.query.delete()
    
    # 为每个设备创建2-5个告警
    for device in devices:
        for _ in range(random.randint(2, 5)):
            alert_time = now - timedelta(hours=random.randint(1, 72))
            alert_type_key = random.choice(list(alert_types_map.keys()))
            alert_type = alert_types_map[alert_type_key]
            severity_key = random.choice(list(severity_map.keys()))
            severity = severity_map[severity_key]
            
            # 设置告警触发值和阈值
            value = 0
            threshold = 0
            
            if alert_type == 'traffic_high':
                value = random.uniform(850, 950)
                threshold = 800
                title = f"设备 {device.name} 流量超过阈值"
                message = f"设备 {device.name} 流量突增，达到 {value:.2f} Mbps，超过阈值 {threshold} Mbps"
            elif alert_type == 'cpu_high':
                value = random.uniform(90, 99)
                threshold = 85
                title = f"设备 {device.name} CPU使用率过高"
                message = f"设备 {device.name} CPU使用率达到 {value:.2f}%，超过阈值 {threshold}%"
            elif alert_type == 'memory_high':
                value = random.uniform(85, 98)
                threshold = 80
                title = f"设备 {device.name} 内存使用率过高"
                message = f"设备 {device.name} 内存使用率达到 {value:.2f}%，超过阈值 {threshold}%"
            elif alert_type == 'device_down':
                title = f"设备 {device.name} 无法连接"
                message = f"设备 {device.name} 连续3次ping不通，可能已经离线"
            elif alert_type == 'security_threat':
                title = f"设备 {device.name} 安全威胁"
                message = f"设备 {device.name} 检测到可疑访问尝试，可能存在安全风险"
            
            alert = Alert(
                device_id=device.id,
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                value=value,
                threshold=threshold,
                is_read=random.choice([True, False]),
                is_handled=random.choice([True, False]),
                created_at=alert_time
            )
            db.session.add(alert)
    
    print("创建告警数据")
    
    # 创建终端数据
    # 先清除之前的终端数据
    Terminal.query.delete()
    
    terminal_types = ['PC', '笔记本', '服务器', '平板', '手机']
    os_list = ['Windows 10', 'Windows 11', 'macOS', 'Ubuntu 20.04', 'CentOS 7', 'Android', 'iOS']
    
    # 随机生成50个终端
    for i in range(1, 51):
        ip_last = i + 100  # 从192.168.1.101开始
        mac_addr = ':'.join([f'{random.randint(0, 255):02x}' for _ in range(6)])
        terminal_type = random.choice(terminal_types)
        os_name = random.choice(os_list)
        
        # 按照终端类型选择位置
        location = random.choice(['教学楼', '实验室', '办公室', '宿舍', '图书馆'])
        
        # 随机连接到一个设备上
        device = random.choice(devices)
        
        terminal = Terminal(
            mac_address=mac_addr,
            ip_address=f"192.168.1.{ip_last}",
            hostname=f"HOST-{i:03d}",
            device_type=terminal_type,
            os_type=os_name,
            is_active=True,
            first_seen=now - timedelta(days=random.randint(1, 30)),
            last_seen=now - timedelta(minutes=random.randint(0, 120)),
            in_traffic=random.randint(500000, 5000000),
            out_traffic=random.randint(500000, 5000000)
        )
        db.session.add(terminal)
    
    print("创建终端数据")
    
    # 提交所有更改
    db.session.commit()
    print("示例数据初始化完成!")

if __name__ == '__main__':
    app = create_app('development')
    with app.app_context():
        init_sample_data() 