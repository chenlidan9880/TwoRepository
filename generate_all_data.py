#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
校园网络监控系统 - 一键生成所有模拟数据
整合了多个单独脚本的功能，可以一次性生成所有需要的模拟数据
"""

import os
import sys
import random
import networkx as nx
import numpy as np
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import json
from sqlalchemy import func
import argparse

# 导入Flask相关模块
from app import create_app, db
from app.models.user import User
from app.models.device import Device
from app.models.terminal import Terminal
from app.models.traffic import Traffic, TrafficStats
from app.models.alert import Alert
from app.models.settings import Settings

# 全局变量
app = None

# =====================================================================
# 辅助函数
# =====================================================================

def setup_app():
    """初始化Flask应用"""
    global app
    app = create_app()
    print(f"初始化应用成功，数据库连接: {app.config['SQLALCHEMY_DATABASE_URI']}")
    return app

def clear_database():
    """清理数据库中的所有数据"""
    with app.app_context():
        print("开始清理数据库...")
        
        try:
            print("删除告警数据...")
            Alert.query.delete()
            db.session.commit()
        except Exception as e:
            print(f"删除告警数据出错: {str(e)}")
            db.session.rollback()
            
        try:
            print("删除流量统计数据...")
            TrafficStats.query.delete()
            db.session.commit()
        except Exception as e:
            print(f"删除流量统计数据出错: {str(e)}")
            db.session.rollback()
            
        try:
            print("删除流量记录数据...")
            Traffic.query.delete()
            db.session.commit()
        except Exception as e:
            print(f"删除流量记录数据出错: {str(e)}")
            db.session.rollback()
            
        try:
            print("删除终端数据...")
            Terminal.query.delete()
            db.session.commit()
        except Exception as e:
            print(f"删除终端数据出错: {str(e)}")
            db.session.rollback()
            
        try:
            print("删除设备数据...")
            Device.query.delete()
            db.session.commit()
        except Exception as e:
            print(f"删除设备数据出错: {str(e)}")
            db.session.rollback()
        
        print("数据库清理完成")

def create_admin_user(username, password):
    """创建管理员用户"""
    with app.app_context():
        print("检查管理员用户...")
        admin = User.query.filter_by(username=username).first()
        if admin is None:
            admin = User(
                username=username,
                email=f"{username}@example.com",
                password_hash=generate_password_hash(password),
                role='admin',
                name='系统管理员',
                department='网络信息中心',
                is_admin=True,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.session.add(admin)
            db.session.commit()
            print(f"创建管理员用户成功: {username} / {password}")
        else:
            print("管理员用户已存在，跳过创建")

def create_basic_settings():
    """创建基本系统设置"""
    with app.app_context():
        print("创建基本系统设置...")
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
        print("基本系统设置创建完成")

# =====================================================================
# 主要功能模块
# =====================================================================

def generate_network_topology(num_terminals=50):
    """创建网络拓扑结构，包括设备和终端"""
    with app.app_context():
        print("开始生成网络拓扑结构...")
        # 创建网络拓扑图
        G = nx.Graph()
        
        # 网络区域定义
        campus_areas = [
            {"name": "行政楼", "subnets": ["192.168.1.0/24"]},
            {"name": "教学楼A", "subnets": ["192.168.2.0/24", "192.168.3.0/24"]},
            {"name": "教学楼B", "subnets": ["192.168.4.0/24", "192.168.5.0/24"]},
            {"name": "图书馆", "subnets": ["192.168.6.0/24"]},
            {"name": "学生宿舍1区", "subnets": ["192.168.7.0/24", "192.168.8.0/24"]},
            {"name": "学生宿舍2区", "subnets": ["192.168.9.0/24", "192.168.10.0/24"]},
            {"name": "食堂", "subnets": ["192.168.11.0/24"]},
            {"name": "体育馆", "subnets": ["192.168.12.0/24"]},
            {"name": "科研楼", "subnets": ["192.168.13.0/24", "192.168.14.0/24"]},
            {"name": "网络中心", "subnets": ["10.0.0.0/24"]}
        ]
        
        # 添加主干设备
        print("创建核心路由器...")
        core_router = create_or_update_device("核心路由器", "10.0.0.1", "网络中心", "router")
        G.add_node(core_router.id, type="router", name=core_router.name)
        
        # 添加汇聚层设备
        print("创建汇聚层交换机...")
        aggregation_switches = []
        for i, area in enumerate(campus_areas):
            ip = f"10.0.0.{i+10}"
            switch = create_or_update_device(f"{area['name']}汇聚交换机", ip, area['name'], "switch")
            aggregation_switches.append(switch)
            G.add_node(switch.id, type="switch", name=switch.name)
            # 连接到核心路由器
            G.add_edge(core_router.id, switch.id, weight=1)
        
        # 添加接入层设备
        print("创建接入层设备...")
        access_devices = []
        for i, area in enumerate(campus_areas):
            for j, subnet in enumerate(area['subnets']):
                # 提取网段前缀
                prefix = subnet.split('/')[0].rsplit('.', 1)[0]
                # 接入层交换机
                ip = f"{prefix}.1"
                
                # 为网络中心使用特殊的IP范围避免与核心路由器冲突
                if area['name'] == "网络中心":
                    ip = f"10.0.1.{j+1}"  # 使用10.0.1.x网段代替10.0.0.x
                
                switch_name = f"{area['name']}接入交换机{j+1}"
                switch = create_or_update_device(switch_name, ip, area['name'], "switch")
                access_devices.append(switch)
                G.add_node(switch.id, type="switch", name=switch.name)
                # 连接到汇聚交换机
                G.add_edge(aggregation_switches[i].id, switch.id, weight=1)
                
                # 每个接入交换机添加1-2个无线AP
                for k in range(random.randint(1, 2)):
                    if area['name'] == "网络中心":
                        ip = f"10.0.1.{100+k}"  # 使用10.0.1.1xx网段
                    else:
                        ip = f"{prefix}.{200+k}"
                    ap_name = f"{area['name']}无线AP{j+1}-{k+1}"
                    ap = create_or_update_device(ap_name, ip, area['name'], "wireless")
                    G.add_node(ap.id, type="wireless", name=ap.name)
                    # 连接到接入交换机
                    G.add_edge(switch.id, ap.id, weight=1)
                    access_devices.append(ap)
        
        # 提交所有设备
        db.session.commit()
        
        # 创建终端设备并连接到接入设备
        print(f"创建{num_terminals}个终端设备...")
        terminal_types = [
            {"type": "PC", "os": ["Windows 10", "Windows 11", "macOS", "Linux"], 
             "vendor": ["Dell", "HP", "Lenovo", "Apple", "Asus"]},
            {"type": "笔记本", "os": ["Windows 10", "Windows 11", "macOS"], 
             "vendor": ["Dell", "HP", "Lenovo", "Apple", "Asus"]},
            {"type": "手机", "os": ["Android", "iOS"], 
             "vendor": ["Samsung", "Apple", "Xiaomi", "Huawei", "OPPO"]},
            {"type": "平板", "os": ["Android", "iOS"], 
             "vendor": ["Samsung", "Apple", "Xiaomi", "Huawei"]},
            {"type": "服务器", "os": ["Windows Server", "CentOS", "Ubuntu Server"], 
             "vendor": ["Dell", "HP", "IBM", "Lenovo"]}
        ]
        
        # 一次性查询所有现有终端的IP和MAC地址
        existing_ips = {ip[0] for ip in db.session.query(Terminal.ip_address).all() if ip[0]}
        existing_macs = {mac[0] for mac in db.session.query(Terminal.mac_address).all() if mac[0]}
        
        # 跟踪新分配的IP和MAC地址
        used_ips = set(existing_ips)
        used_macs = set(existing_macs)
        
        print(f"数据库中现有IP地址:{len(existing_ips)}个，MAC地址:{len(existing_macs)}个")
        
        # 生成并保存终端
        terminals = []
        created_count = 0
        
        # 为避免无限循环，设置最大尝试次数
        max_attempts = num_terminals * 5
        attempts = 0
        
        while created_count < num_terminals and attempts < max_attempts:
            attempts += 1
            # 随机选择一个接入设备
            access_device = random.choice(access_devices)
            
            # 随机选择一个终端类型
            terminal_type_info = random.choice(terminal_types)
            device_type = terminal_type_info["type"]
            os_type = random.choice(terminal_type_info["os"])
            vendor = random.choice(terminal_type_info["vendor"])
            
            # 为终端生成唯一的IP地址
            area_name = access_device.location
            # 找到该区域的子网
            area = next((a for a in campus_areas if a["name"] == area_name), None)
            subnet = random.choice(area["subnets"]) if area else "192.168.1.0/24"
            prefix = subnet.split('/')[0].rsplit('.', 1)[0]
            
            # 尝试生成唯一IP，避免与已知记录冲突
            ip_address = None
            for _ in range(50):  # 每个终端最多尝试50次IP
                ip_last_octet = random.randint(100, 250)
                potential_ip = f"{prefix}.{ip_last_octet}"
                if potential_ip not in used_ips:
                    ip_address = potential_ip
                    used_ips.add(ip_address)
                    break
            
            if ip_address is None:
                # 如果无法分配IP，尝试下一台终端
                continue
            
            # 生成唯一的MAC地址
            mac_address = None
            
            # 生成两部分MAC地址：厂商前缀(OUI)和设备特定部分
            oui_prefixes = {
                "Dell": ["00:14:22", "00:24:E8", "D4:BE:D9"],
                "HP": ["00:0F:61", "00:25:B3", "94:57:A5"],
                "Lenovo": ["00:09:2D", "60:D9:C7", "88:70:8C"],
                "Apple": ["00:03:93", "00:1F:F3", "AC:BC:32"],
                "Asus": ["00:1B:FC", "04:92:26", "50:46:5D"],
                "Samsung": ["00:23:39", "00:26:5F", "84:25:DB"],
                "Xiaomi": ["00:9E:C8", "28:E3:1F", "64:09:80"],
                "Huawei": ["00:18:82", "28:31:52", "70:7B:E8"],
                "OPPO": ["0C:91:60", "1C:77:F6", "2C:5B:E1"],
                "IBM": ["00:09:6B", "00:18:B1", "FC:CF:62"],
            }
            
            for _ in range(50):  # 每个终端最多尝试50次MAC
                # 选择厂商特定的OUI前缀
                vendor_prefixes = oui_prefixes.get(vendor, ["00:00:00"])
                chosen_prefix = random.choice(vendor_prefixes)
                
                # 生成后三个字节
                suffix_bytes = [random.randint(0, 255) for _ in range(3)]
                suffix = ':'.join([f'{b:02x}' for b in suffix_bytes])
                
                potential_mac = f"{chosen_prefix}:{suffix}"
                
                if potential_mac not in used_macs:
                    mac_address = potential_mac
                    used_macs.add(mac_address)
                    break
            
            if mac_address is None:
                # 如果无法分配MAC，尝试下一台终端
                continue
            
            # 生成主机名 - 确保唯一
            hostname = f"HOST-{random.randint(1, 999):03d}-{created_count:03d}"
            
            # 生成位置
            location = random.choice(['教学楼', '实验室', '办公室', '宿舍', '图书馆'])
            
            # 根据是否为无线AP决定连接类型
            connection_type = "wireless" if access_device.device_type == "wireless" else "wired"
            
            # 创建终端对象
            terminal = Terminal(
                hostname=hostname,
                ip_address=ip_address,
                mac_address=mac_address,
                device_type=device_type,
                os_type=os_type,
                vendor=vendor,
                connected_device_id=access_device.id,
                is_active=random.random() > 0.2,  # 80%概率在线
                location=location,
                connection_type=connection_type,
                port_number=f"Gi0/{random.randint(1, 24)}" if connection_type == "wired" else None,
                vlan_id=str(random.randint(10, 50)) if connection_type == "wired" else None,
                user_agent=generate_user_agent(device_type, os_type, vendor),
                first_seen=datetime.now() - timedelta(days=random.randint(1, 30)),
                last_seen=datetime.now() - timedelta(minutes=random.randint(0, 120)),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 根据终端类型分配不同的流量数据
            if device_type in ["PC", "服务器"]:
                in_traffic = random.randint(50000000, 5000000000)  # 50MB-5GB
                out_traffic = random.randint(10000000, 1000000000)  # 10MB-1GB
            elif device_type in ["笔记本"]:
                in_traffic = random.randint(30000000, 3000000000)  # 30MB-3GB
                out_traffic = random.randint(8000000, 800000000)  # 8MB-800MB
            else:  # 手机和平板
                in_traffic = random.randint(10000000, 1000000000)  # 10MB-1GB
                out_traffic = random.randint(5000000, 500000000)  # 5MB-500MB
            
            terminal.in_traffic = in_traffic
            terminal.out_traffic = out_traffic
            terminal.bandwidth_usage = random.uniform(0.01, 0.5)  # 1%-50%
            
            db.session.add(terminal)
            terminals.append(terminal)
            
            created_count += 1
            
            # 每20个终端提交一次，避免内存问题
            if len(terminals) % 20 == 0:
                db.session.commit()
                print(f"已创建 {created_count} 个终端设备... (尝试次数: {attempts})")
        
        # 提交剩余终端
        db.session.commit()
        
        # 输出终端生成结果统计
        if created_count < num_terminals:
            print(f"警告：只创建了 {created_count}/{num_terminals} 个终端设备，可能是因为IP地址或MAC地址空间不足")
        else:
            print(f"成功创建了 {created_count} 个终端设备")
            
        print(f"网络拓扑生成完成！共创建 {Device.query.count()} 个网络设备和 {Terminal.query.count()} 个终端设备")
        
        return G, Device.query.all(), Terminal.query.all()

def create_or_update_device(name, ip_address, location, device_type):
    """创建或更新网络设备"""
    # 先查找是否已存在同名设备
    existing_device = Device.query.filter_by(name=name).first()
    
    if existing_device:
        # 更新现有设备信息
        existing_device.ip_address = ip_address
        existing_device.location = location
        existing_device.device_type = device_type
        existing_device.updated_at = datetime.now()
        db.session.add(existing_device)
        db.session.flush()  # 确保ID生成但不提交事务
        return existing_device
    else:
        # 创建新设备
        device = Device(
            name=name,
            ip_address=ip_address,
            device_type=device_type,
            location=location,
            snmp_community="public",
            snmp_version="2c",
            snmp_port=161,
            status="online",
            description=f"模拟{device_type}设备",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.session.add(device)
        db.session.flush()  # 确保ID生成但不提交事务
        return device

def generate_user_agent(device_type, os_type, vendor):
    """生成模拟的用户代理字符串"""
    chrome_version = f"{random.randint(80, 108)}.0.{random.randint(1000, 9999)}.{random.randint(10, 200)}"
    safari_version = f"{random.randint(10, 16)}.{random.randint(0, 3)}"
    firefox_version = f"{random.randint(70, 100)}.0"
    edge_version = f"{random.randint(80, 100)}.0.{random.randint(100, 999)}.{random.randint(10, 100)}"
    
    if device_type in ["PC", "笔记本", "服务器"]:
        if "Windows" in os_type:
            window_version = "10.0" if "10" in os_type else "11.0"
            return f"Mozilla/5.0 (Windows NT {window_version}; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
        elif "macOS" in os_type:
            return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randint(12, 15)}_{random.randint(0, 7)}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{safari_version} Safari/605.1.15"
        else:  # Linux
            return f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
    elif device_type in ["手机", "平板"]:
        if os_type == "Android":
            android_version = f"{random.randint(8, 13)}.{random.randint(0, 3)}.{random.randint(0, 3)}"
            return f"Mozilla/5.0 (Linux; Android {android_version}; {vendor} {random.choice(['SM-G970F', 'Pixel 6', 'Redmi Note 10'])}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Mobile Safari/537.36"
        else:  # iOS
            ios_version = f"{random.randint(14, 16)}_{random.randint(0, 5)}"
            device_name = "iPhone" if device_type == "手机" else "iPad"
            return f"Mozilla/5.0 (iPhone; CPU {device_name} OS {ios_version} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{safari_version} Mobile/15E148 Safari/604.1"
    else:
        return "Mozilla/5.0 (compatible; CampusNetworkMonitor/1.0; +http://example.com/bot)"

def generate_traffic_data(devices, terminals, days=7):
    """生成流量数据"""
    with app.app_context():
        print(f"开始生成{days}天的流量数据...")
        
        # 获取当前时间作为结束时间
        end_time = datetime.now()
        # 计算开始时间
        start_time = end_time - timedelta(days=days)
        
        # 为每一小时生成一次数据点
        total_hours = days * 24
        current_time = start_time
        
        # 初始化流量汇总信息
        total_traffic_records = 0
        
        # 模拟不同时间段的流量模式
        time_patterns = {
            "workday": {
                "morning": {"start": 8, "end": 12, "multiplier": 0.8},
                "afternoon": {"start": 13, "end": 17, "multiplier": 0.7},
                "evening": {"start": 18, "end": 22, "multiplier": 0.5},
                "night": {"start": 23, "end": 7, "multiplier": 0.1}
            },
            "weekend": {
                "morning": {"start": 9, "end": 12, "multiplier": 0.4},
                "afternoon": {"start": 13, "end": 17, "multiplier": 0.6},
                "evening": {"start": 18, "end": 23, "multiplier": 0.7},
                "night": {"start": 0, "end": 8, "multiplier": 0.2}
            }
        }
        
        # 批量提交的数据
        batch_traffic_data = []
        batch_size = 100  # 每100条记录提交一次
        
        print(f"计划生成 {total_hours} 小时的数据点...")
        
        # 用于存储设备和终端的流量数据，以便后续计算总流量
        device_traffic = {}  # device_id -> {"in": total_in, "out": total_out}
        terminal_traffic = {}  # terminal_id -> {"in": total_in, "out": total_out}
        
        # 遍历每个小时
        for hour in range(total_hours):
            current_time = start_time + timedelta(hours=hour)
            hour_of_day = current_time.hour
            day_of_month = current_time.day
            month = current_time.month
            year = current_time.year
            
            # 确定当前是工作日还是周末
            is_weekend = current_time.weekday() >= 5  # 5和6是周末
            day_type = "weekend" if is_weekend else "workday"
            
            # 确定一天中的时间段
            current_hour = current_time.hour
            
            # 默认乘数为0.3，用于找不到匹配时间段的情况
            time_multiplier = 0.3
            
            # 寻找当前时间所属的时间段
            for period, period_data in time_patterns[day_type].items():
                start_hour = period_data["start"]
                end_hour = period_data["end"]
                
                # 处理跨天的情况
                if start_hour > end_hour:  # 时间段跨越午夜
                    if current_hour >= start_hour or current_hour < end_hour:
                        time_multiplier = period_data["multiplier"]
                        break
                else:  # 正常情况
                    if start_hour <= current_hour < end_hour:
                        time_multiplier = period_data["multiplier"]
                        break
            
            # 为每个设备生成流量数据
            for device in devices:
                # 如果设备尚未在跟踪字典中，添加它
                if device.id not in device_traffic:
                    device_traffic[device.id] = {"in": 0, "out": 0}
                
                # 根据设备类型设置基础流量
                if device.device_type == "router":
                    base_inbound = random.randint(100000000, 500000000)  # 100MB-500MB
                    base_outbound = random.randint(80000000, 400000000)  # 80MB-400MB
                elif device.device_type == "switch":
                    base_inbound = random.randint(50000000, 200000000)  # 50MB-200MB
                    base_outbound = random.randint(40000000, 150000000)  # 40MB-150MB
                else:  # wireless
                    base_inbound = random.randint(20000000, 100000000)  # 20MB-100MB
                    base_outbound = random.randint(15000000, 80000000)  # 15MB-80MB
                
                # 应用时间乘数调整流量
                inbound = int(base_inbound * time_multiplier * (1 + random.uniform(-0.2, 0.2)))
                outbound = int(base_outbound * time_multiplier * (1 + random.uniform(-0.2, 0.2)))
                
                # 累计总流量
                device_traffic[device.id]["in"] += inbound
                device_traffic[device.id]["out"] += outbound
                
                # 创建流量记录
                traffic_data = Traffic(
                    device_id=device.id,
                    interface="Aggregate",  # 汇总流量
                    in_octets=inbound,
                    out_octets=outbound,
                    in_packets=int(inbound / random.randint(500, 1500)),  # 估算数据包数量
                    out_packets=int(outbound / random.randint(500, 1500)),
                    in_errors=random.randint(0, 10),
                    out_errors=random.randint(0, 5),
                    bandwidth=1000000000,  # 假设1Gbps带宽
                    utilization=random.uniform(0.1, 0.8),  # 10%-80%带宽利用率
                    timestamp=current_time
                )
                
                batch_traffic_data.append(traffic_data)
                
                # 创建每小时流量统计记录
                traffic_stats = TrafficStats(
                    device_id=device.id,
                    hour=hour_of_day,
                    day=day_of_month,
                    month=month,
                    year=year,
                    avg_in_rate=inbound / 3600,  # 转换为bps
                    avg_out_rate=outbound / 3600,
                    max_in_rate=inbound / 3600 * 1.2,  # 估算峰值
                    max_out_rate=outbound / 3600 * 1.2,
                    avg_utilization=random.uniform(0.1, 0.8),
                    peak_time=current_time + timedelta(minutes=random.randint(0, 59)),
                    created_at=datetime.now()
                )
                
                batch_traffic_data.append(traffic_stats)
                
                # 如果批次满了，提交数据
                if len(batch_traffic_data) >= batch_size:
                    db.session.bulk_save_objects(batch_traffic_data)
                    db.session.commit()
                    total_traffic_records += len(batch_traffic_data)
                    batch_traffic_data = []
            
            # 为活跃的终端生成流量数据 (只选择30%的终端以减少数据量)
            active_terminals = [t for t in terminals if t.is_active]
            if active_terminals:  # 确保有活跃终端
                selected_terminals = random.sample(
                    active_terminals, 
                    min(len(active_terminals), max(1, int(len(active_terminals) * 0.3)))
                )
                
                for terminal in selected_terminals:
                    # 如果终端尚未在跟踪字典中，添加它
                    if terminal.id not in terminal_traffic:
                        terminal_traffic[terminal.id] = {"in": 0, "out": 0}
                    
                    # 根据终端类型设置基础流量
                    if terminal.device_type in ["PC", "服务器"]:
                        base_inbound = random.randint(5000000, 50000000)  # 5MB-50MB
                        base_outbound = random.randint(2000000, 20000000)  # 2MB-20MB
                    elif terminal.device_type == "笔记本":
                        base_inbound = random.randint(3000000, 30000000)  # 3MB-30MB
                        base_outbound = random.randint(1000000, 10000000)  # 1MB-10MB
                    else:  # 手机和平板
                        base_inbound = random.randint(1000000, 10000000)  # 1MB-10MB
                        base_outbound = random.randint(500000, 5000000)  # 500KB-5MB
                    
                    # 应用时间乘数调整流量 - 终端通常比设备流量变化更大
                    inbound = int(base_inbound * time_multiplier * (1 + random.uniform(-0.4, 0.4)))
                    outbound = int(base_outbound * time_multiplier * (1 + random.uniform(-0.3, 0.4)))
                    
                    # 累计总流量
                    terminal_traffic[terminal.id]["in"] += inbound
                    terminal_traffic[terminal.id]["out"] += outbound
                    
                    # 创建终端流量记录
                    traffic_data = Traffic(
                        device_id=terminal.connected_device_id,  # 关联到连接的设备
                        interface=f"Terminal-{terminal.id}",  # 使用终端ID作为接口标识
                        in_octets=inbound,
                        out_octets=outbound,
                        in_packets=int(inbound / random.randint(500, 1500)),
                        out_packets=int(outbound / random.randint(500, 1500)),
                        in_errors=random.randint(0, 5),
                        out_errors=random.randint(0, 3),
                        bandwidth=random.choice([100000000, 1000000000]),  # 100Mbps或1Gbps
                        utilization=random.uniform(0.05, 0.5),  # 5%-50%带宽利用率
                        timestamp=current_time
                    )
                    
                    batch_traffic_data.append(traffic_data)
                    
                    # 如果批次满了，提交数据
                    if len(batch_traffic_data) >= batch_size:
                        db.session.bulk_save_objects(batch_traffic_data)
                        db.session.commit()
                        total_traffic_records += len(batch_traffic_data)
                        batch_traffic_data = []
            
            # 每12个小时输出一次进度(每半天)
            if hour % 12 == 0:
                print(f"已生成 {hour} 小时的数据点... ({hour/total_hours*100:.1f}%)")
        
        # 提交剩余的批次数据
        if batch_traffic_data:
            db.session.bulk_save_objects(batch_traffic_data)
            db.session.commit()
            total_traffic_records += len(batch_traffic_data)
        
        # 更新每个终端的总流量
        print("更新终端总流量统计...")
        for terminal_id, traffic in terminal_traffic.items():
            terminal = next((t for t in terminals if t.id == terminal_id), None)
            if terminal:
                terminal.in_traffic = traffic["in"]
                terminal.out_traffic = traffic["out"]
                terminal.bandwidth_usage = random.uniform(0.01, 0.5)  # 1%-50%
        
        # 保存所有终端的流量统计更新
        db.session.commit()
        
        print(f"流量数据生成完成！共创建 {total_traffic_records} 条流量记录")
        print(f"时间范围: {start_time} 到 {end_time}")
        
        return total_traffic_records

def generate_alerts(devices, count_per_device=3):
    """生成告警数据"""
    with app.app_context():
        print("开始生成告警数据...")
        
        # 告警类型定义
        alert_types = [
            {
                "type": "系统资源",
                "subtypes": [
                    {"name": "CPU使用率过高", "level": "warning", "probability": 0.3, "value_range": [80, 95], "threshold_range": [70, 80]},
                    {"name": "内存使用率过高", "level": "warning", "probability": 0.3, "value_range": [80, 95], "threshold_range": [70, 80]},
                    {"name": "存储空间不足", "level": "warning", "probability": 0.2, "value_range": [85, 95], "threshold_range": [75, 85]},
                    {"name": "系统温度过高", "level": "danger", "probability": 0.1, "value_range": [70, 90], "threshold_range": [60, 70]}
                ]
            },
            {
                "type": "网络连接",
                "subtypes": [
                    {"name": "网络接口故障", "level": "danger", "probability": 0.2, "value_range": [0, 0], "threshold_range": [1, 1]},
                    {"name": "链路状态变更", "level": "info", "probability": 0.5, "value_range": [0, 1], "threshold_range": [1, 1]},
                    {"name": "网络拥塞", "level": "warning", "probability": 0.3, "value_range": [85, 99], "threshold_range": [70, 80]},
                    {"name": "网络延迟过高", "level": "warning", "probability": 0.3, "value_range": [150, 500], "threshold_range": [50, 100]}
                ]
            },
            {
                "type": "安全事件",
                "subtypes": [
                    {"name": "可疑登录尝试", "level": "danger", "probability": 0.2, "value_range": [5, 20], "threshold_range": [3, 5]},
                    {"name": "未授权访问", "level": "danger", "probability": 0.15, "value_range": [1, 10], "threshold_range": [0, 0]},
                    {"name": "端口扫描检测", "level": "warning", "probability": 0.25, "value_range": [10, 100], "threshold_range": [5, 10]},
                    {"name": "异常流量模式", "level": "warning", "probability": 0.3, "value_range": [200, 500], "threshold_range": [150, 200]},
                    {"name": "DDoS攻击尝试", "level": "danger", "probability": 0.05, "value_range": [10000, 1000000], "threshold_range": [5000, 10000]}
                ]
            },
            {
                "type": "设备状态",
                "subtypes": [
                    {"name": "设备重启", "level": "info", "probability": 0.4, "value_range": [1, 1], "threshold_range": [0, 0]},
                    {"name": "设备离线", "level": "danger", "probability": 0.2, "value_range": [0, 0], "threshold_range": [1, 1]},
                    {"name": "配置变更", "level": "warning", "probability": 0.3, "value_range": [1, 10], "threshold_range": [0, 0]},
                    {"name": "硬件故障", "level": "danger", "probability": 0.1, "value_range": [1, 1], "threshold_range": [0, 0]}
                ]
            }
        ]
        
        # 生成告警的时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        
        total_alerts = 0
        batch_alerts = []
        batch_size = 50
        
        # 告警处理状态定义
        status_options = {
            "未处理": {"is_read": False, "is_handled": False, "is_recovered": False},
            "处理中": {"is_read": True, "is_handled": True, "is_recovered": False},
            "已解决": {"is_read": True, "is_handled": True, "is_recovered": True},
            "已关闭": {"is_read": True, "is_handled": True, "is_recovered": True}
        }
        
        for device in devices:
            # 设备告警数量 - 增加一些随机性
            num_alerts = max(1, int(count_per_device * (1 + random.uniform(-0.5, 0.5))))
            
            for _ in range(num_alerts):
                # 随机选择一个告警类型组
                alert_type_group = random.choice(alert_types)
                alert_type = alert_type_group["type"]
                
                # 从该组中根据概率选择一个子类型
                subtype_choices = []
                subtype_weights = []
                
                for subtype in alert_type_group["subtypes"]:
                    subtype_choices.append(subtype)
                    subtype_weights.append(subtype["probability"])
                
                # 归一化权重
                sum_weights = sum(subtype_weights)
                normalized_weights = [w/sum_weights for w in subtype_weights]
                
                # 选择子类型
                selected_subtype = random.choices(subtype_choices, weights=normalized_weights, k=1)[0]
                
                # 随机生成告警时间
                alert_time = start_time + timedelta(
                    seconds=random.randint(0, int((end_time - start_time).total_seconds()))
                )
                
                # 确定告警状态 - 较早的告警更可能被处理
                time_factor = (end_time - alert_time).total_seconds() / (end_time - start_time).total_seconds()
                status_choices = ["未处理", "处理中", "已解决", "已关闭"]
                status_weights = [
                    0.3 * (1 - time_factor),  # 较早的告警不太可能是未处理
                    0.3 * (1 - time_factor/2),
                    0.2 + 0.4 * time_factor,  # 较早的告警更可能已解决
                    0.2 + 0.3 * time_factor   # 较早的告警更可能已关闭
                ]
                status = random.choices(status_choices, weights=status_weights, k=1)[0]
                
                # 生成告警详情描述
                message = generate_alert_details(device, selected_subtype["name"], alert_type)
                
                # 生成随机值和阈值
                value_min, value_max = selected_subtype["value_range"]
                threshold_min, threshold_max = selected_subtype["threshold_range"]
                
                value = random.uniform(value_min, value_max)
                threshold = random.uniform(threshold_min, threshold_max)
                
                # 生成告警标题
                title = f"{selected_subtype['name']} - {device.name}"
                
                # 设置告警处理状态
                status_attrs = status_options[status]
                
                # 创建告警对象
                alert = Alert(
                    device_id=device.id,
                    alert_type=alert_type,
                    title=title,  # 使用title代替alert_name
                    severity=selected_subtype["level"],
                    message=message,  # 使用message代替details
                    value=value,
                    threshold=threshold,
                    is_read=status_attrs["is_read"],
                    is_handled=status_attrs["is_handled"],
                    is_recovered=status_attrs["is_recovered"],
                    created_at=alert_time
                )
                
                # 设置已读时间
                if status_attrs["is_read"]:
                    alert.read_at = alert_time + timedelta(minutes=random.randint(5, 60))
                
                # 设置处理时间
                if status_attrs["is_handled"]:
                    alert.handled_at = alert_time + timedelta(minutes=random.randint(10, 120))
                    # 随机指定一个管理员用户作为处理人
                    admin_users = User.query.filter_by(is_admin=True).all()
                    if admin_users:
                        alert.handled_by = random.choice(admin_users).id
                
                # 设置恢复时间
                if status_attrs["is_recovered"]:
                    alert.recovered_at = alert_time + timedelta(minutes=random.randint(30, 240))
                
                batch_alerts.append(alert)
                
                # 如果批次满了，提交数据
                if len(batch_alerts) >= batch_size:
                    db.session.bulk_save_objects(batch_alerts)
                    db.session.commit()
                    total_alerts += len(batch_alerts)
                    batch_alerts = []
        
        # 提交剩余的批次数据
        if batch_alerts:
            db.session.bulk_save_objects(batch_alerts)
            db.session.commit()
            total_alerts += len(batch_alerts)
        
        print(f"告警数据生成完成！共创建 {total_alerts} 条告警记录")
        return total_alerts

def generate_alert_details(device, alert_name, alert_type):
    """生成告警的详细描述"""
    device_name = device.name
    device_ip = device.ip_address
    device_type = device.device_type
    
    # 系统资源类告警详情
    if alert_type == "系统资源":
        if "CPU" in alert_name:
            cpu_usage = random.randint(80, 100)
            threshold = random.choice([75, 80, 85, 90])
            return (f"设备 {device_name} (IP: {device_ip}) CPU使用率达到{cpu_usage}%，超过预设阈值{threshold}%。"
                    f"持续时间: {random.randint(5, 30)}分钟。建议检查设备负载情况。")
        
        elif "内存" in alert_name:
            mem_usage = random.randint(80, 95)
            threshold = random.choice([75, 80, 85])
            return (f"设备 {device_name} (IP: {device_ip}) 内存使用率达到{mem_usage}%，超过预设阈值{threshold}%。"
                    f"可用内存不足，可能影响设备性能。")
        
        elif "存储" in alert_name:
            storage_usage = random.randint(85, 98)
            threshold = random.choice([80, 85, 90])
            return (f"设备 {device_name} (IP: {device_ip}) 存储空间使用率达到{storage_usage}%，超过预设阈值{threshold}%。"
                    f"剩余可用空间: {random.randint(1, 15)}GB。请及时清理日志和临时文件。")
        
        elif "温度" in alert_name:
            temp = random.randint(70, 95)
            threshold = random.choice([65, 70, 75])
            return (f"设备 {device_name} (IP: {device_ip}) 温度达到{temp}°C，超过安全阈值{threshold}°C。"
                    f"持续高温可能导致硬件损坏。请检查设备散热系统。")
    
    # 网络连接类告警详情
    elif alert_type == "网络连接":
        if "接口故障" in alert_name:
            interface = f"GigabitEthernet1/{random.randint(0, 24)}"
            return (f"设备 {device_name} (IP: {device_ip}) 接口 {interface} 出现物理层故障。"
                    f"接口状态: down，持续时间: {random.randint(1, 60)}分钟。可能原因: 线缆损坏或接口硬件故障。")
        
        elif "链路状态" in alert_name:
            interface = f"GigabitEthernet1/{random.randint(0, 24)}"
            state = random.choice(["up", "down"])
            return (f"设备 {device_name} (IP: {device_ip}) 接口 {interface} 链路状态变更为 {state}。"
                    f"变更时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}。")
        
        elif "拥塞" in alert_name:
            interface = f"GigabitEthernet1/{random.randint(0, 24)}"
            utilization = random.randint(85, 99)
            return (f"设备 {device_name} (IP: {device_ip}) 接口 {interface} 带宽利用率达到{utilization}%。"
                    f"可能导致网络延迟增加和数据包丢失。建议检查流量特征并考虑带宽扩容。")
        
        elif "延迟" in alert_name:
            latency = random.randint(100, 500)
            threshold = random.choice([50, 75, 100])
            return (f"设备 {device_name} (IP: {device_ip}) 网络延迟达到{latency}ms，超过正常阈值{threshold}ms。"
                    f"可能影响实时应用和用户体验。建议检查网络拥塞情况。")
    
    # 安全事件类告警详情
    elif alert_type == "安全事件":
        if "登录" in alert_name:
            source_ip = f"10.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
            attempts = random.randint(5, 20)
            return (f"设备 {device_name} (IP: {device_ip}) 检测到来自 {source_ip} 的多次失败登录尝试，"
                    f"共{attempts}次尝试。疑似密码暴力破解攻击。已临时阻止该IP访问。")
        
        elif "未授权访问" in alert_name:
            source_ip = f"10.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
            resource = random.choice(["管理界面", "配置文件", "敏感数据", "系统资源"])
            return (f"设备 {device_name} (IP: {device_ip}) 检测到来自 {source_ip} 的未授权访问尝试。"
                    f"目标资源: {resource}。访问已被系统阻止并记录。建议检查设备访问控制列表。")
        
        elif "端口扫描" in alert_name:
            source_ip = f"10.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
            ports = random.randint(10, 100)
            return (f"设备 {device_name} (IP: {device_ip}) 检测到来自 {source_ip} 的端口扫描活动。"
                    f"在{random.randint(1, 10)}分钟内扫描了{ports}个端口。可能是网络侦察行为，建议监控该IP的后续活动。")
        
        elif "异常流量" in alert_name:
            protocol = random.choice(["TCP", "UDP", "ICMP", "HTTP", "DNS"])
            increase = random.randint(200, 800)
            return (f"设备 {device_name} (IP: {device_ip}) 检测到异常{protocol}流量模式。"
                    f"流量增长{increase}%，偏离正常基线。可能表明网络行为异常或安全事件。")
        
        elif "DDoS" in alert_name:
            attack_type = random.choice(["SYN洪水", "UDP洪水", "DNS放大", "HTTP洪水"])
            pps = random.randint(10000, 1000000)
            return (f"设备 {device_name} (IP: {device_ip}) 检测到可能的{attack_type}DDoS攻击。"
                    f"流量峰值: {pps}包/秒。目标: {device_ip}。已启动流量清洗和过滤措施。")
    
    # 设备状态类告警详情
    elif alert_type == "设备状态":
        if "重启" in alert_name:
            uptime = random.randint(1, 60)
            return (f"设备 {device_name} (IP: {device_ip}) 于{datetime.now() - timedelta(minutes=uptime)}完成重启。"
                    f"当前运行时间: {uptime}分钟。重启原因: {random.choice(['计划维护', '手动重启', '系统崩溃', '电源故障', '未知原因'])}。")
        
        elif "离线" in alert_name:
            duration = random.randint(5, 120)
            return (f"设备 {device_name} (IP: {device_ip}) 已离线{duration}分钟。"
                    f"最后响应时间: {(datetime.now() - timedelta(minutes=duration)).strftime('%Y-%m-%d %H:%M:%S')}。"
                    f"已尝试通过ICMP、SNMP和远程管理协议联系设备，均无响应。建议现场检查设备状态。")
        
        elif "配置变更" in alert_name:
            user = random.choice(["admin", "operator", "system", "maintenance", "remote"])
            return (f"设备 {device_name} (IP: {device_ip}) 配置已被用户'{user}'修改。"
                    f"变更时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}。"
                    f"变更内容: {random.choice(['访问控制列表', '路由表', '接口配置', 'VLAN配置', '系统参数'])}。")
        
        elif "硬件故障" in alert_name:
            component = random.choice(["电源模块", "风扇", "接口卡", "内存模块", "CPU", "背板"])
            return (f"设备 {device_name} (IP: {device_ip}) 检测到{component}硬件故障。"
                    f"故障开始时间: {datetime.now() - timedelta(hours=random.randint(1, 12))}。"
                    f"设备{random.choice(['仍在正常运行但性能下降', '部分功能受到影响', '处于降级模式'])}。建议尽快安排硬件维修或更换。")
    
    # 默认详情
    return f"设备 {device_name} (IP: {device_ip}) 触发{alert_name}告警。请系统管理员检查设备状态。"

# =====================================================================
# 主函数与命令行处理
# =====================================================================

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="一键生成校园网监控系统的模拟数据")
    
    parser.add_argument('--clear-db', action='store_true', help='清空数据库中的所有数据')
    parser.add_argument('--terminals', type=int, default=50, help='要生成的终端数量，默认50')
    parser.add_argument('--traffic-days', type=int, default=7, help='要生成的流量数据天数，默认7')
    parser.add_argument('--alerts-per-device', type=int, default=3, help='每个设备生成的告警数量，默认3')
    parser.add_argument('--admin-username', type=str, default='admin', help='管理员用户名，默认admin')
    parser.add_argument('--admin-password', type=str, default='admin123', help='管理员密码，默认admin123')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    # 初始化应用
    global app
    app = setup_app()
    
    # 显示欢迎信息
    print("=" * 80)
    print("校园网监控系统 - 模拟数据生成工具")
    print("=" * 80)
    print(f"数据生成参数:")
    print(f"- 终端数量: {args.terminals}")
    print(f"- 流量数据天数: {args.traffic_days}")
    print(f"- 每设备告警数: {args.alerts_per_device}")
    if args.clear_db:
        print("- 将清空数据库")
    print("=" * 80)
    
    # 可选清空数据库
    if args.clear_db:
        if input("确认清空数据库? 这将删除所有现有数据! (y/n): ").lower() == 'y':
            clear_database()
        else:
            print("跳过数据库清空...")
    
    # 创建基础数据
    create_admin_user(args.admin_username, args.admin_password)
    create_basic_settings()
    
    start_time = datetime.now()
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 生成网络拓扑
    G, devices, terminals = generate_network_topology(num_terminals=args.terminals)
    
    # 生成流量数据
    traffic_count = generate_traffic_data(devices, terminals, days=args.traffic_days)
    
    # 生成告警数据
    alert_count = generate_alerts(devices, count_per_device=args.alerts_per_device)
    
    # 输出生成统计
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print("\n" + "=" * 80)
    print("数据生成完成!")
    print("=" * 80)
    print(f"设备数量: {len(devices)}")
    print(f"终端数量: {len(terminals)}")
    print(f"流量记录数: {traffic_count}")
    print(f"告警记录数: {alert_count}")
    print(f"总耗时: {duration:.2f} 秒")
    print("=" * 80)
    
    print("\n系统现在包含以下数据:")
    with app.app_context():
        print(f"- 设备总数: {Device.query.count()}")
        print(f"- 终端总数: {Terminal.query.count()}")
        print(f"- 流量记录总数: {TrafficStats.query.count()}")
        print(f"- 告警记录总数: {Alert.query.count()}")
    
    print("\n您现在可以启动应用并登录查看生成的数据。")
    print(f"管理员账号: {args.admin_username}")
    print(f"管理员密码: {args.admin_password}")

if __name__ == "__main__":
    main() 