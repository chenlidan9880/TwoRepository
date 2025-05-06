#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
生成模拟流量数据
"""

from app import create_app, db
from app.models.device import Device
from app.models.traffic import Traffic
from datetime import datetime, timedelta
import random
import sys

def generate_traffic_data(days=3, samples_per_day=24*12):
    """生成模拟流量数据
    
    Args:
        days: 生成多少天的数据
        samples_per_day: 每天生成多少个样本（默认每5分钟一个样本）
    """
    app = create_app()
    with app.app_context():
        # 获取所有设备
        devices = Device.query.all()
        if not devices:
            print("没有设备，请先运行add_test_data.py添加测试设备")
            return False
        
        print(f"开始为{len(devices)}个设备生成{days}天的模拟流量数据...")
        
        # 设置带宽范围（单位：Mbps）
        bandwidths = {
            'switch': (100, 1000),  # 交换机 100Mbps-1Gbps
            'router': (1000, 10000),  # 路由器 1Gbps-10Gbps
            'wireless': (54, 300)  # 无线设备 54Mbps-300Mbps
        }
        
        # 删除现有的流量数据
        Traffic.query.delete()
        db.session.commit()
        
        # 设置开始和结束时间
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # 计算时间间隔
        interval = timedelta(days=days) / samples_per_day
        
        # 为每个设备生成数据
        for device in devices:
            print(f"为设备 {device.name} 生成流量数据...")
            
            # 确定设备带宽范围
            device_type = device.device_type or 'switch'
            min_bw, max_bw = bandwidths.get(device_type, bandwidths['switch'])
            
            # 设备带宽（Mbps）
            bandwidth = random.randint(min_bw, max_bw)
            
            # 生成数据点
            current_time = start_time
            traffic_data_list = []
            
            while current_time <= end_time:
                # 按照时间段生成不同的流量模式
                hour = current_time.hour
                # 白天（8点-18点）流量较高
                if 8 <= hour < 18:
                    # 工作时间，流量波动较大
                    utilization = random.uniform(0.3, 0.8)  # 30%-80%利用率
                    variance = 0.3  # 高波动
                # 晚上（18点-23点）流量中等
                elif 18 <= hour < 23:
                    # 娱乐时间，流量中等
                    utilization = random.uniform(0.2, 0.5)  # 20%-50%利用率
                    variance = 0.2  # 中波动
                # 深夜（23点-8点）流量较低
                else:
                    # 深夜时间，流量较低
                    utilization = random.uniform(0.05, 0.2)  # 5%-20%利用率
                    variance = 0.1  # 低波动
                
                # 计算当前流量
                base_traffic_mbps = bandwidth * utilization
                
                # 加入随机波动
                in_traffic_mbps = max(0, base_traffic_mbps * (1 + random.uniform(-variance, variance)))
                out_traffic_mbps = max(0, base_traffic_mbps * (1 + random.uniform(-variance, variance)))
                
                # 转换为字节/秒
                in_octets = int(in_traffic_mbps * 1000000 / 8)  # Mbps转为字节/秒
                out_octets = int(out_traffic_mbps * 1000000 / 8)  # Mbps转为字节/秒
                
                # 创建流量记录
                traffic = Traffic(
                    device_id=device.id,
                    timestamp=current_time,
                    in_octets=in_octets,
                    out_octets=out_octets,
                    in_errors=int(in_octets * random.uniform(0, 0.001)),  # 0-0.1%的错误率
                    out_errors=int(out_octets * random.uniform(0, 0.001)),  # 0-0.1%的错误率
                    in_discards=int(in_octets * random.uniform(0, 0.002)),  # 0-0.2%的丢弃率
                    out_discards=int(out_octets * random.uniform(0, 0.002)),  # 0-0.2%的丢弃率
                    utilization=utilization * 100,  # 转换为百分比
                    bandwidth=bandwidth  # 带宽（Mbps）
                )
                
                traffic_data_list.append(traffic)
                
                # 时间递增
                current_time += interval
            
            # 批量添加数据
            db.session.add_all(traffic_data_list)
            db.session.commit()
            
            print(f"已为设备 {device.name} 生成 {len(traffic_data_list)} 条流量数据")
        
        # 总结
        total_records = Traffic.query.count()
        print(f"完成模拟数据生成，共生成 {total_records} 条流量记录")
        return True

if __name__ == "__main__":
    try:
        # 默认生成3天的数据，每5分钟一个样本点
        days = 3
        samples_per_day = 24 * 12  # 每5分钟一个样本，一天有288个样本
        
        # 如果提供了参数，则使用参数
        if len(sys.argv) > 1:
            days = int(sys.argv[1])
        if len(sys.argv) > 2:
            samples_per_day = int(sys.argv[2])
        
        generate_traffic_data(days, samples_per_day)
    except Exception as e:
        print(f"生成模拟数据时出错: {str(e)}")
        sys.exit(1) 