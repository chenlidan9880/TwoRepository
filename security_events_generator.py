#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
网络安全事件生成模块 - 生成网络安全事件和异常流量模式
"""

import numpy as np
import random
import json
import os
import sys
from datetime import datetime, timedelta
from app import create_app, db
from app.models.device import Device
from app.models.terminal import Terminal
from app.models.traffic import Traffic
from app.models.alert import Alert

def generate_random_ip():
    """生成随机IP地址"""
    return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

def generate_event_details(event, target_type, target_name):
    """生成事件详细信息的JSON字符串"""
    details = {
        'event_type': event['type'],
        'target_type': target_type,
        'target_name': target_name,
        'detection_method': random.choice(['流量分析', '签名匹配', '行为异常', '机器学习检测']),
        'confidence': random.randint(70, 99),
        'recommended_action': random.choice([
            '检查设备安全配置', '隔离受影响设备', '更新防火墙规则', 
            '进行深度安全扫描', '监控相关设备'
        ])
    }
    
    # 根据事件类型添加特定信息
    if event['type'] == 'DDoS攻击模拟':
        details.update({
            'attack_vector': random.choice(['TCP SYN Flood', 'UDP Flood', 'HTTP Flood', 'ICMP Flood']),
            'peak_traffic': f"{random.randint(500, 10000)} Mbps",
            'packet_signature': f"源端口: {random.randint(1, 65535)}, 目标端口: {random.randint(1, 65535)}"
        })
    elif event['type'] == '端口扫描':
        details.update({
            'scanned_ports': [random.randint(1, 65535) for _ in range(random.randint(5, 15))],
            'scan_pattern': random.choice(['顺序扫描', '随机扫描', 'SYN扫描', 'FIN扫描']),
            'scan_duration': f"{random.randint(2, 10)}分钟"
        })
    elif event['type'] == '异常流量峰值':
        details.update({
            'normal_baseline': f"{random.randint(10, 100)} Mbps",
            'peak_value': f"{random.randint(200, 1000)} Mbps",
            'affected_services': random.choice(['HTTP/HTTPS', 'DNS', 'SMB', '数据库服务', '所有服务'])
        })
    elif event['type'] == '可疑连接':
        details.update({
            'destination_ip': generate_random_ip(),
            'destination_port': random.randint(1, 65535),
            'connection_protocol': random.choice(['TCP', 'UDP', 'HTTP', 'HTTPS']),
            'data_transfer': f"{random.randint(1, 100)}MB"
        })
    elif event['type'] == '网络扫描':
        details.update({
            'scan_range': f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.0/24",
            'discovery_protocol': random.choice(['ARP', 'ICMP', 'TCP SYN']),
            'scan_duration': f"{random.randint(5, 30)}分钟"
        })
    
    return json.dumps(details, ensure_ascii=False)

# 各种异常流量模式的实现
def ddos_traffic_pattern(target_id, start_time, end_time, is_device=True):
    """模拟DDoS攻击的流量模式"""
    # 获取时间范围内的所有流量记录
    if is_device:
        traffic_records = Traffic.query.filter(
            Traffic.device_id == target_id,
            Traffic.timestamp.between(start_time, end_time)
        ).all()
        
        for record in traffic_records:
            # 显著增加入站流量，适度增加出站流量
            record.in_octets = int(record.in_octets * random.uniform(10, 50))  # 增加10-50倍
            record.in_packets = int(record.in_packets * random.uniform(20, 100))  # 更多的小包
            record.out_octets = int(record.out_octets * random.uniform(1.5, 3))  # 增加1.5-3倍
            record.out_packets = int(record.out_packets * random.uniform(1.5, 3))
            
            # 显著增加错误率
            record.in_errors = int(record.in_packets * random.uniform(0.05, 0.2))  # 5-20%错误率
            record.utilization = min(100, record.utilization * random.uniform(5, 15))  # 大幅提高利用率
            
            db.session.add(record)
    else:
        # 如果是终端，更新终端流量
        terminal = Terminal.query.get(target_id)
        if terminal:
            # 显著增加入站和出站流量
            terminal.in_traffic = int(terminal.in_traffic * random.uniform(8, 20))
            terminal.out_traffic = int(terminal.out_traffic * random.uniform(2, 5))
            terminal.bandwidth_usage = min(1.0, terminal.bandwidth_usage * random.uniform(5, 10))
            db.session.add(terminal)
    
    db.session.commit()

def port_scan_traffic_pattern(target_id, start_time, end_time, is_device=True):
    """模拟端口扫描的流量模式"""
    if is_device:
        traffic_records = Traffic.query.filter(
            Traffic.device_id == target_id,
            Traffic.timestamp.between(start_time, end_time)
        ).all()
        
        for record in traffic_records:
            # 端口扫描通常以大量小包为特征
            record.in_packets = int(record.in_packets * random.uniform(3, 8))  # 增加3-8倍
            # 但是总流量不会增加太多
            record.in_octets = int(record.in_octets * random.uniform(1.2, 2))  # 增加1.2-2倍
            # 响应流量也会增加
            record.out_packets = int(record.out_packets * random.uniform(2, 5))  # 增加2-5倍
            record.out_octets = int(record.out_octets * random.uniform(1.1, 1.5))  # 增加1.1-1.5倍
            
            db.session.add(record)
    else:
        terminal = Terminal.query.get(target_id)
        if terminal:
            # 终端流量特征
            terminal.out_traffic = int(terminal.out_traffic * random.uniform(2, 4))
            terminal.in_traffic = int(terminal.in_traffic * random.uniform(1.5, 3))
            terminal.bandwidth_usage = min(1.0, terminal.bandwidth_usage * random.uniform(1.5, 3))
            db.session.add(terminal)
    
    db.session.commit()

def traffic_spike_pattern(target_id, start_time, end_time, is_device=True):
    """模拟流量突增的模式"""
    if is_device:
        traffic_records = Traffic.query.filter(
            Traffic.device_id == target_id,
            Traffic.timestamp.between(start_time, end_time)
        ).all()
        
        for record in traffic_records:
            # 流量突增：入站和出站流量都会增加
            multiplier = random.uniform(3, 10)  # 3-10倍流量增长
            record.in_octets = int(record.in_octets * multiplier)
            record.out_octets = int(record.out_octets * multiplier)
            record.in_packets = int(record.in_packets * multiplier)
            record.out_packets = int(record.out_packets * multiplier)
            record.utilization = min(100, record.utilization * multiplier)
            
            db.session.add(record)
    else:
        terminal = Terminal.query.get(target_id)
        if terminal:
            multiplier = random.uniform(4, 12)
            terminal.in_traffic = int(terminal.in_traffic * multiplier)
            terminal.out_traffic = int(terminal.out_traffic * multiplier)
            terminal.bandwidth_usage = min(1.0, terminal.bandwidth_usage * multiplier)
            db.session.add(terminal)
    
    db.session.commit()

def suspicious_connection_pattern(target_id, start_time, end_time, is_device=True):
    """模拟可疑连接的流量模式"""
    # 可疑连接通常不会导致流量大幅增加，但会有持续的小流量
    if is_device:
        traffic_records = Traffic.query.filter(
            Traffic.device_id == target_id,
            Traffic.timestamp.between(start_time, end_time)
        ).all()
        
        for record in traffic_records:
            # 轻微增加流量
            record.in_octets = int(record.in_octets * random.uniform(1.1, 1.5))
            record.out_octets = int(record.out_octets * random.uniform(1.05, 1.3))
            record.in_packets = int(record.in_packets * random.uniform(1.2, 1.6))
            record.out_packets = int(record.out_packets * random.uniform(1.1, 1.4))
            
            db.session.add(record)
    else:
        terminal = Terminal.query.get(target_id)
        if terminal:
            terminal.in_traffic = int(terminal.in_traffic * random.uniform(1.2, 1.8))
            terminal.out_traffic = int(terminal.out_traffic * random.uniform(1.1, 1.6))
            # 可疑连接可能会导致带宽使用率波动
            terminal.bandwidth_usage = min(1.0, terminal.bandwidth_usage * random.uniform(1.3, 2.0))
            db.session.add(terminal)
    
    db.session.commit()

def network_scan_pattern(target_id, start_time, end_time, is_device=True):
    """模拟网络扫描的流量模式"""
    if is_device:
        traffic_records = Traffic.query.filter(
            Traffic.device_id == target_id,
            Traffic.timestamp.between(start_time, end_time)
        ).all()
        
        for record in traffic_records:
            # 网络扫描通常体现为大量小包
            record.out_packets = int(record.out_packets * random.uniform(5, 15))  # 增加5-15倍
            record.out_octets = int(record.out_octets * random.uniform(1.5, 3))  # 增加1.5-3倍
            # 响应通常较少
            record.in_packets = int(record.in_packets * random.uniform(2, 6))  # 增加2-6倍
            record.in_octets = int(record.in_octets * random.uniform(1.2, 2))  # 增加1.2-2倍
            
            db.session.add(record)
    else:
        terminal = Terminal.query.get(target_id)
        if terminal:
            # 终端进行网络扫描
            terminal.out_traffic = int(terminal.out_traffic * random.uniform(3, 8))
            terminal.in_traffic = int(terminal.in_traffic * random.uniform(1.5, 4))
            terminal.bandwidth_usage = min(1.0, terminal.bandwidth_usage * random.uniform(2, 5))
            db.session.add(terminal)
    
    db.session.commit()

def generate_security_events(days=7, clear_existing=True):
    """生成网络安全事件和异常流量模式"""
    app = create_app()
    with app.app_context():
        # 获取所有设备和终端
        devices = Device.query.all()
        terminals = Terminal.query.all()
        
        if not devices or not terminals:
            print("没有设备或终端，请先生成基础网络数据")
            return False
        
        print(f"开始生成{days}天的网络安全事件和异常流量模式...")
        
        # 预先定义的安全事件类型
        security_events = [
            {
                'type': 'DDoS攻击模拟', 
                'description': '检测到可能的DDoS攻击流量',
                'severity': 'critical',
                'duration': timedelta(minutes=random.randint(15, 60)),
                'traffic_pattern': ddos_traffic_pattern
            },
            {
                'type': '端口扫描', 
                'description': '检测到可能的端口扫描活动',
                'severity': 'warning',
                'duration': timedelta(minutes=random.randint(5, 20)),
                'traffic_pattern': port_scan_traffic_pattern
            },
            {
                'type': '异常流量峰值', 
                'description': '检测到流量异常峰值',
                'severity': 'warning',
                'duration': timedelta(minutes=random.randint(10, 30)),
                'traffic_pattern': traffic_spike_pattern
            },
            {
                'type': '可疑连接', 
                'description': '检测到终端与可疑IP地址的连接',
                'severity': 'medium',
                'duration': timedelta(minutes=random.randint(5, 15)),
                'traffic_pattern': suspicious_connection_pattern
            },
            {
                'type': '网络扫描', 
                'description': '检测到网络范围扫描活动',
                'severity': 'medium',
                'duration': timedelta(minutes=random.randint(15, 45)),
                'traffic_pattern': network_scan_pattern
            }
        ]
        
        # 清除之前的告警
        if clear_existing:
            try:
                print("删除现有告警数据...")
                Alert.query.delete()
                db.session.commit()
            except Exception as e:
                print(f"删除告警数据出错: {str(e)}")
                db.session.rollback()
        
        # 生成随机时间点的安全事件
        start_time = datetime.now() - timedelta(days=days)
        end_time = datetime.now()
        
        # 决定要生成多少个安全事件
        num_events = random.randint(10, 20)
        generated_alerts = []
        
        for _ in range(num_events):
            # 随机选择事件类型
            event = random.choice(security_events)
            
            # 随机选择发生事件的时间
            event_time = start_time + random.random() * (end_time - start_time)
            
            # 随机选择涉及的设备/终端
            if random.random() > 0.5:  # 50%概率事件涉及网络设备
                target = random.choice(devices)
                target_type = 'device'
                target_id = target.id
                target_name = target.name
                target_ip = target.ip_address
                device_id = target.id
            else:  # 50%概率事件涉及终端设备
                target = random.choice(terminals)
                target_type = 'terminal'
                target_id = target.id
                target_name = target.hostname
                target_ip = target.ip_address
                device_id = target.connected_device_id
            
            # 生成告警详情
            details = generate_event_details(event, target_type, target_name)
            
            # 根据告警模型字段创建告警
            if 'medium' in event['severity']:
                severity = 'warning'
            else:
                severity = event['severity']
                
            alert = Alert(
                device_id=device_id,  # 如果是终端，关联到其连接的设备
                alert_type='security_event',
                severity=severity,
                title=event['type'],
                message=f"{event['description']}，来源IP: {target_ip}",
                value=random.uniform(70, 100),  # 置信度
                threshold=70,  # 阈值
                is_read=False,
                is_handled=False,
                is_recovered=False,
                created_at=event_time
            )
            
            db.session.add(alert)
            generated_alerts.append({
                'alert': alert,
                'event': event,
                'target_type': target_type,
                'target_id': target_id,
                'start_time': event_time,
                'end_time': event_time + event['duration']
            })
        
        db.session.commit()
        print(f"已生成 {len(generated_alerts)} 个安全事件告警")
        
        # 生成对应的异常流量
        print("开始生成对应的异常流量模式...")
        for alert_info in generated_alerts:
            # 获取事件时间段
            start_time = alert_info['start_time']
            end_time = alert_info['end_time']
            
            # 生成异常流量模式
            event = alert_info['event']
            target_id = alert_info['target_id']
            target_type = alert_info['target_type']
            
            if target_type == 'device':
                # 为网络设备生成异常流量
                event['traffic_pattern'](target_id, start_time, end_time, is_device=True)
            else:
                # 为终端设备生成异常流量
                event['traffic_pattern'](target_id, start_time, end_time, is_device=False)
        
        print(f"成功生成{len(generated_alerts)}个安全事件和对应的异常流量模式")
        return True

if __name__ == "__main__":
    try:
        # 参数
        days = 7
        clear_existing = True
        
        # 如果提供了参数，则使用参数
        if len(sys.argv) > 1:
            days = int(sys.argv[1])
        if len(sys.argv) > 2:
            clear_existing = sys.argv[2].lower() != 'false' and sys.argv[2] != '0'
        
        print(f"生成安全事件: {days}天, 清除现有数据: {clear_existing}")
        generate_security_events(days, clear_existing)
        print("安全事件生成完成！")
    except Exception as e:
        print(f"生成安全事件时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 