#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试流量数据加载脚本 - 验证流量数据是否正确存储在数据库中
"""

from datetime import datetime, timedelta
from app import create_app, db
from app.models.device import Device
from app.models.traffic import Traffic

def test_traffic_data():
    """测试流量数据加载"""
    app = create_app()
    with app.app_context():
        # 获取所有设备
        devices = Device.query.all()
        
        if not devices:
            print("没有找到设备")
            return
        
        print(f"系统中共有 {len(devices)} 个设备")
        
        # 选择第一个设备进行测试
        device = devices[0]
        print(f"测试设备: {device.name}, ID: {device.id}")
        
        # 设置查询时间范围
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        # 计算总流量记录数
        total_records = Traffic.query.filter(
            Traffic.device_id == device.id
        ).count()
        print(f"该设备总流量记录数: {total_records}")
        
        # 获取按小时间隔的流量数据
        traffic_data = db.session.query(
            db.func.date_format(Traffic.timestamp, '%H:00').label('hour'),
            db.func.sum(Traffic.in_octets).label('in_traffic'),
            db.func.sum(Traffic.out_octets).label('out_traffic')
        ).filter(
            Traffic.device_id == device.id,
            Traffic.timestamp.between(start_time, end_time)
        ).group_by('hour').all()
        
        print(f"按小时分组后的记录数: {len(traffic_data)}")
        
        # 打印每小时的流量数据
        print("\n时间\t入站流量(MB)\t出站流量(MB)")
        print("-" * 40)
        
        if traffic_data:
            for data in traffic_data:
                in_mb = float(data.in_traffic) / (1024*1024) if data.in_traffic else 0
                out_mb = float(data.out_traffic) / (1024*1024) if data.out_traffic else 0
                print(f"{data.hour}\t{in_mb:.2f}\t\t{out_mb:.2f}")
        else:
            print("没有找到流量数据")
        
        # 检查数据格式
        if traffic_data:
            print("\n数据类型检查:")
            sample = traffic_data[0]
            print(f"hour类型: {type(sample.hour)}")
            print(f"in_traffic类型: {type(sample.in_traffic)}")
            print(f"out_traffic类型: {type(sample.out_traffic)}")
            
            # 测试转换为JSON
            hours = [data.hour for data in traffic_data]
            in_traffic = [float(data.in_traffic) / (1024*1024) for data in traffic_data]
            out_traffic = [float(data.out_traffic) / (1024*1024) for data in traffic_data]
            
            import json
            json_data = {
                'hours': hours,
                'in_traffic': in_traffic,
                'out_traffic': out_traffic
            }
            
            json_str = json.dumps(json_data)
            print(f"\nJSON数据示例: {json_str[:200]}...")

if __name__ == "__main__":
    test_traffic_data() 