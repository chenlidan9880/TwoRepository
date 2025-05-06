#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
网络拓扑生成模块 - 使用图论模型生成更真实的网络拓扑和设备关系
"""

import networkx as nx
import numpy as np
import random
import json
from datetime import datetime, timedelta
import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# 修复日志文件权限问题
# 确保日志目录存在
os.makedirs('logs', exist_ok=True)

# 覆盖默认的RotatingFileHandler以忽略文件权限错误
class SafeRotatingFileHandler(RotatingFileHandler):
    def doRollover(self):
        try:
            super().doRollover()
        except PermissionError:
            print("警告: 无法轮换日志文件，可能被其他进程锁定")
            pass  # 忽略权限错误

# 修改默认的RotatingFileHandler
logging.handlers.RotatingFileHandler = SafeRotatingFileHandler

from app import create_app, db
from app.models.device import Device
from app.models.terminal import Terminal

def generate_random_mac():
    """生成随机MAC地址"""
    return ":".join(["{:02x}".format(random.randint(0, 255)) for _ in range(6)])

def generate_user_agent(device_type, os_type, vendor=""):
    """生成符合设备类型和操作系统的User-Agent字符串"""
    if device_type == "PC":
        if "Windows" in os_type:
            return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 110)}.0.0.0 Safari/537.36"
        elif "macOS" in os_type:
            return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randint(13, 15)}_{random.randint(1, 7)}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{random.randint(13, 16)}.{random.randint(0, 3)} Safari/605.1.15"
        else:  # Linux
            return f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 110)}.0.0.0 Safari/537.36"
    elif device_type == "Mobile":
        if os_type == "Android":
            return f"Mozilla/5.0 (Linux; Android {random.randint(9, 13)}; SM-G{random.randint(900, 999)}0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 110)}.0.0.0 Mobile Safari/537.36"
        else:  # iOS
            return f"Mozilla/5.0 (iPhone; CPU iPhone OS {random.randint(13, 16)}_{random.randint(0, 6)} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{random.randint(13, 16)}.0 Mobile/15E148 Safari/604.1"
    else:  # IoT
        return f"EmbeddedDevice/{random.randint(1, 5)}.{random.randint(0, 9)} ({vendor}; {device_type})"


def create_device(name, ip_address, location, device_type):
    """创建或更新网络设备"""
    # 先查找是否已存在同名设备
    existing_device = Device.query.filter_by(name=name).first()

    if existing_device:
        print(f"找到现有设备: {name}，更新信息而不是创建新设备")
        # 更新现有设备信息
        existing_device.ip_address = ip_address
        existing_device.location = location
        existing_device.device_type = device_type
        existing_device.updated_at = datetime.now()
        db.session.add(existing_device)
        db.session.commit()
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
        db.session.commit()
        print(f"创建新设备: {name}")
        return device


def create_terminal(hostname, ip_address, mac_address, device_type, os_type, vendor, connected_device, location):
    """创建并添加新的终端设备"""
    terminal = Terminal(
        hostname=hostname,
        ip_address=ip_address,
        mac_address=mac_address,
        device_type=device_type,
        os_type=os_type,
        vendor=vendor,
        connected_device_id=connected_device.id,
        is_active=random.random() > 0.2,  # 80%概率在线
        location=location,
        connection_type="wireless" if connected_device.device_type == "wireless" else "wired",
        port_number=f"Gi0/{random.randint(1, 24)}" if connected_device.device_type == "switch" else None,
        vlan_id=str(random.randint(10, 50)) if connected_device.device_type == "switch" else None,
        user_agent=generate_user_agent(device_type, os_type, vendor)
    )
    
    # 随机生成流量数据
    if device_type == "PC":
        in_traffic = random.randint(50000000, 5000000000)  # 50MB-5GB
        out_traffic = random.randint(10000000, 1000000000)  # 10MB-1GB
    elif device_type == "Mobile":
        in_traffic = random.randint(10000000, 1000000000)  # 10MB-1GB
        out_traffic = random.randint(5000000, 500000000)  # 5MB-500MB
    else:  # IoT设备
        in_traffic = random.randint(1000000, 100000000)  # 1MB-100MB
        out_traffic = random.randint(500000, 50000000)  # 500KB-50MB
    
    terminal.in_traffic = in_traffic
    terminal.out_traffic = out_traffic
    terminal.bandwidth_usage = random.uniform(0.01, 0.5)  # 1%-50%
    terminal.first_seen = datetime.now() - timedelta(days=random.randint(1, 30))
    terminal.last_seen = datetime.now() - timedelta(minutes=random.randint(0, 120))
    
    db.session.add(terminal)
    return terminal

def generate_network_topology(clear_existing=True):
    """生成校园网络拓扑结构和设备间的关系"""
    # 创建应用实例
    app = create_app()
    
    with app.app_context():
        # 创建网络拓扑图
        G = nx.Graph()
        
        # 删除现有设备和终端
        if clear_existing:
            from app.models.traffic import Traffic
            try:
                print("删除现有流量数据...")
                Traffic.query.delete()
                db.session.commit()
            except Exception as e:
                print(f"删除流量数据出错: {str(e)}")
                db.session.rollback()
            
            try:
                print("删除现有终端设备...")
                Terminal.query.delete()
                db.session.commit()
            except Exception as e:
                print(f"删除终端数据出错: {str(e)}")
                db.session.rollback()
                
            try:
                print("删除现有网络设备...")
                Device.query.delete()
                db.session.commit()
            except Exception as e:
                print(f"删除设备数据出错: {str(e)}")
                db.session.rollback()
        
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
        
        print("开始生成网络设备和拓扑...")
        # 添加主干设备
        core_router = create_device("核心路由器", "10.0.0.1", "网络中心", "router")
        print(f"创建核心路由器: ID={core_router.id}, 名称={core_router.name}")
        G.add_node(core_router.id, type="router", name=core_router.name)
        
        # 添加汇聚层设备
        aggregation_switches = []
        for i, area in enumerate(campus_areas):
            ip = f"10.0.0.{i+10}"
            switch = create_device(f"{area['name']}汇聚交换机", ip, area['name'], "switch")
            print(f"创建汇聚交换机: ID={switch.id}, 名称={switch.name}")
            aggregation_switches.append(switch)
            G.add_node(switch.id, type="switch", name=switch.name)
            # 连接到核心路由器
            G.add_edge(core_router.id, switch.id, weight=1)
        
        # 添加接入层设备
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
                switch = create_device(switch_name, ip, area['name'], "switch")
                print(f"创建接入交换机: ID={switch.id}, 名称={switch.name}")
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
                    ap = create_device(ap_name, ip, area['name'], "wireless")
                    print(f"创建无线AP: ID={ap.id}, 名称={ap.name}")
                    G.add_node(ap.id, type="wireless", name=ap.name)
                    # 连接到接入交换机
                    G.add_edge(switch.id, ap.id, weight=1)
                    access_devices.append(ap)
        
        # 提交所有设备
        db.session.commit()
        print(f"已创建 {Device.query.count()} 个网络设备")
        
        print("开始生成终端设备...")
        # 创建终端设备并连接到接入设备
        terminal_types = [
            {"type": "PC", "os": ["Windows 10", "Windows 11", "macOS", "Linux"], 
             "vendor": ["Dell", "HP", "Lenovo", "Apple", "Asus"]},
            {"type": "Mobile", "os": ["Android", "iOS"], 
             "vendor": ["Samsung", "Apple", "Xiaomi", "Huawei", "OPPO"]},
            {"type": "IoT", "os": ["Embedded"], 
             "vendor": ["Cisco", "TP-Link", "Hikvision", "Dahua"]}
        ]
        
        # 跟踪已分配的IP地址
        used_ips = set()
        # 跟踪已分配的MAC地址
        used_macs = set()
        
        terminals_count = 0
        for area in campus_areas:
            for subnet in area['subnets']:
                # 确定这个子网对应的接入设备
                prefix = subnet.split('/')[0].rsplit('.', 1)[0]
                
                # 为网络中心使用特殊的IP范围
                is_network_center = area['name'] == "网络中心"
                
                # 查找匹配的接入设备
                if is_network_center:
                    # 网络中心使用10.0.1.x网段的设备
                    access_device = next((d for d in access_devices 
                                         if d.ip_address.startswith("10.0.1") and 
                                         d.location == "网络中心"), None)
                else:
                    access_device = next((d for d in access_devices 
                                         if d.ip_address.startswith(prefix)), None)
                
                if access_device:
                    # 为每个子网创建一定数量的终端
                    num_terminals = random.randint(5, 10)  # 减少数量以加快处理
                    for i in range(num_terminals):
                        # 生成唯一的终端IP地址
                        ip_address = None
                        for _ in range(100):  # 尝试最多100次找到唯一IP
                            if is_network_center:
                                # 网络中心终端使用10.0.2.x网段
                                ip_last_octet = random.randint(10, 99)
                                potential_ip = f"10.0.2.{ip_last_octet}"
                            else:
                                ip_last_octet = random.randint(100, 199)
                                potential_ip = f"{prefix}.{ip_last_octet}"
                                
                            if potential_ip not in used_ips:
                                ip_address = potential_ip
                                used_ips.add(ip_address)
                                break
                        
                        # 如果无法生成唯一IP，则跳过此终端
                        if not ip_address:
                            print(f"警告：无法为{area['name']}分配唯一IP，跳过创建终端")
                            continue
                        
                        # 生成唯一的MAC地址
                        mac_address = None
                        for _ in range(100):  # 尝试最多100次找到唯一MAC
                            potential_mac = generate_random_mac()
                            if potential_mac not in used_macs:
                                mac_address = potential_mac
                                used_macs.add(mac_address)
                                break
                        
                        # 如果无法生成唯一MAC，则跳过此终端
                        if not mac_address:
                            print(f"警告：无法为{area['name']}分配唯一MAC，跳过创建终端")
                            # 移除已分配的IP以便重用
                            used_ips.remove(ip_address)
                            continue
                        
                        # 随机选择终端类型
                        terminal_type = random.choice(terminal_types)
                        device_type = terminal_type["type"]
                        os_type = random.choice(terminal_type["os"])
                        vendor = random.choice(terminal_type["vendor"])
                        
                        # 创建终端
                        terminal_name = f"{area['name']}终端{i+1}"
                        try:
                            create_terminal(terminal_name, ip_address, mac_address,
                                           device_type, os_type, vendor, 
                                           access_device, area['name'])
                            terminals_count += 1
                            # 定期提交以避免事务过大
                            if terminals_count % 10 == 0:
                                db.session.commit()
                                print(f"已创建 {terminals_count} 个终端设备")
                        except Exception as e:
                            print(f"创建终端 {terminal_name} (IP: {ip_address}) 失败: {str(e)}")
                            db.session.rollback()
                            # 移除失败的IP
                            used_ips.remove(ip_address)
        
        # 提交所有终端
        try:
            db.session.commit()
            print(f"终端设备创建完成，共 {terminals_count} 个")
        except Exception as e:
            print(f"提交终端数据时出错: {str(e)}")
            db.session.rollback()
        
        # 将网络拓扑导出为JSON格式保存（可用于可视化）
        try:
            topology_data = nx.node_link_data(G)
            os.makedirs('data', exist_ok=True)
            with open('data/network_topology.json', 'w') as f:
                json.dump(topology_data, f)
            print("已保存网络拓扑到data/network_topology.json")
        except Exception as e:
            print(f"保存网络拓扑JSON时出错: {str(e)}")
        
        print(f"已生成网络拓扑，共 {Device.query.count()} 个网络设备和 {Terminal.query.count()} 个终端设备")
        
        # 返回图对象，可用于后续流量模拟
        return G

if __name__ == "__main__":
    try:
        # 确保输出目录存在
        os.makedirs('data', exist_ok=True)
        
        # 生成网络拓扑
        clear_existing = True
        if len(sys.argv) > 1:
            if sys.argv[1].lower() == 'false' or sys.argv[1] == '0':
                clear_existing = False
        
        print(f"生成网络拓扑，清除现有数据: {clear_existing}")
        generate_network_topology(clear_existing)
        print("网络拓扑生成完成！")
    except Exception as e:
        print(f"生成网络拓扑时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 