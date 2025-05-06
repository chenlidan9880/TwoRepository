#!/usr/bin/env python
"""
数据采集工具
用于通过命令行手动触发网络设备数据采集
"""

import sys
import argparse
from datetime import datetime
from app import create_app, db
from app.models.device import Device
from app.models.traffic import Traffic
from app.utils.snmp_collector import (
    poll_device_traffic, poll_device_resources,
    get_interfaces, calculate_bandwidth_utilization
)

def collect_all_devices(args):
    """
    采集所有设备的数据
    
    参数:
        args: 命令行参数
    
    返回:
        成功的设备数量
    """
    print("开始采集所有设备数据...")
    devices = Device.query.all()
    
    if not devices:
        print("没有发现设备。请先添加设备。")
        return 0
    
    success_count = 0
    total_count = len(devices)
    
    for device in devices:
        if collect_device_data(device, args):
            success_count += 1
    
    print(f"数据采集完成。成功: {success_count}/{total_count}")
    return success_count

def collect_device_data(device, args):
    """
    采集单个设备的数据
    
    参数:
        device: 设备对象
        args: 命令行参数
    
    返回:
        成功返回True，失败返回False
    """
    print(f"正在采集设备 {device.name} (IP: {device.ip_address}) 的数据...")
    
    try:
        # 检查并更新设备状态
        old_status = device.status
        
        # 采集流量数据
        traffic_data = poll_device_traffic(
            device.ip_address,
            port=device.snmp_port,
            community=device.snmp_community,
            version=device.snmp_version
        )
        
        if not traffic_data:
            if not args.quiet:
                print(f"设备 {device.name} (IP: {device.ip_address}) 采集失败")
            
            if device.status != 'offline':
                device.status = 'offline'
                device.updated_at = datetime.now()
                db.session.commit()
                print(f"设备 {device.name} 状态更新为离线")
            
            return False
        
        # 更新设备状态为在线
        if device.status != 'online':
            device.status = 'online'
            device.updated_at = datetime.now()
            db.session.commit()
            if old_status != 'online':
                print(f"设备 {device.name} 状态更新为在线")
        
        # 采集资源数据（仅支持特定设备）
        resource_data = poll_device_resources(
            device.ip_address,
            port=device.snmp_port,
            community=device.snmp_community,
            version=device.snmp_version
        )
        
        if resource_data:
            device.cpu_usage = resource_data.get('cpu_usage', 0)
            device.memory_usage = resource_data.get('memory_usage', 0)
            device.updated_at = datetime.now()
            db.session.commit()
            if not args.quiet:
                print(f"设备 {device.name} 资源数据已更新: CPU {device.cpu_usage}%, 内存 {device.memory_usage}%")
        
        # 获取接口列表和描述
        interfaces = get_interfaces(
            device.ip_address,
            port=device.snmp_port,
            community=device.snmp_community,
            version=device.snmp_version
        )
        
        # 获取时间戳
        timestamp = datetime.now()
        
        # 保存流量数据
        for interface_index, data in traffic_data.items():
            interface_name = interfaces.get(interface_index, f"Interface {interface_index}")
            speed = data.get('speed', 100000000)  # 默认100Mbps
            in_bytes = data.get('in_bytes', 0)
            out_bytes = data.get('out_bytes', 0)
            
            # 计算带宽利用率
            in_bps = data.get('in_bps', 0)
            out_bps = data.get('out_bps', 0)
            utilization = calculate_bandwidth_utilization(in_bps + out_bps, speed)
            
            # 创建流量记录
            traffic = Traffic(
                device_id=device.id,
                interface=interface_name,
                interface_index=interface_index,
                inbound=in_bytes,
                outbound=out_bytes,
                bandwidth_utilization=utilization,
                timestamp=timestamp
            )
            
            db.session.add(traffic)
        
        # 提交数据库更改
        db.session.commit()
        
        if not args.quiet:
            print(f"设备 {device.name} (IP: {device.ip_address}) 数据采集成功")
        
        return True
    except Exception as e:
        db.session.rollback()
        print(f"采集设备 {device.name} (IP: {device.ip_address}) 数据时出错: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='SNMP数据采集工具')
    parser.add_argument('--device', help='指定设备ID或IP地址，不指定则采集所有设备')
    parser.add_argument('-q', '--quiet', action='store_true', help='安静模式，只显示错误信息')
    
    args = parser.parse_args()
    
    app = create_app()
    with app.app_context():
        if args.device:
            # 按ID或IP地址查找设备
            try:
                device_id = int(args.device)
                device = Device.query.get(device_id)
            except ValueError:
                device = Device.query.filter_by(ip_address=args.device).first()
            
            if not device:
                print(f"未找到设备: {args.device}")
                return
            
            if collect_device_data(device, args):
                print(f"设备 {device.name} 数据采集成功")
        else:
            collect_all_devices(args)

if __name__ == '__main__':
    main() 