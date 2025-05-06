#!/usr/bin/env python
"""
流量监控系统测试脚本
用于测试流量收集、处理和统计功能
"""

from app import create_app, db
from app.models.device import Device
from app.models.traffic import Traffic, TrafficStats
from app.utils.traffic_collector import collect_device_traffic, collect_all_devices_traffic
from app.utils.traffic_processor import process_traffic_stats, process_daily_stats
from datetime import datetime, timedelta
import random
import time

def test_traffic_collection():
    """测试流量收集功能"""
    print("===== 测试流量收集功能 =====")
    app = create_app()
    
    with app.app_context():
        # 查询所有在线设备
        devices = Device.query.filter_by(status='online').all()
        print(f"在线设备数量: {len(devices)}")
        
        if not devices:
            print("没有在线设备，请先添加或更新设备状态")
            return
        
        # 为每个设备收集流量数据
        for device in devices:
            print(f"收集设备 {device.name} (ID: {device.id}) 的流量数据...")
            traffic_data = collect_device_traffic(device)
            print(f"已收集 {len(traffic_data)} 个接口的流量数据")
        
        # 查询最新的流量记录
        latest_traffic = Traffic.query.order_by(Traffic.timestamp.desc()).first()
        if latest_traffic:
            print(f"最新流量记录: 设备ID={latest_traffic.device_id}, 接口={latest_traffic.interface}, 时间={latest_traffic.timestamp}")
            print(f"入站流量: {latest_traffic.in_octets * 8 / 5 / 1000000:.2f} Mbps, 出站流量: {latest_traffic.out_octets * 8 / 5 / 1000000:.2f} Mbps")
            print(f"利用率: {latest_traffic.utilization:.2f}%")
        else:
            print("没有找到流量记录")

def test_traffic_stats_processing():
    """测试流量统计处理功能"""
    print("\n===== 测试流量统计处理功能 =====")
    app = create_app()
    
    with app.app_context():
        # 查询现有的统计数据
        existing_stats = TrafficStats.query.count()
        print(f"现有统计数据数量: {existing_stats}")
        
        # 处理流量统计
        print("处理小时级别流量统计...")
        start_time = time.time()
        result = process_traffic_stats()
        end_time = time.time()
        print(f"处理结果: {result}, 耗时: {end_time - start_time:.2f} 秒")
        
        # 查询处理后的统计数据
        new_stats = TrafficStats.query.count()
        print(f"处理后统计数据数量: {new_stats}, 新增: {new_stats - existing_stats}")
        
        # 查看最新的统计数据
        latest_stats = TrafficStats.query.order_by(TrafficStats.created_at.desc()).first()
        if latest_stats:
            print(f"最新统计数据: 设备ID={latest_stats.device_id}, 时间={latest_stats.year}-{latest_stats.month}-{latest_stats.day} {latest_stats.hour}时")
            print(f"平均入站流量: {latest_stats.avg_in_rate / 1000000:.2f} Mbps, 平均出站流量: {latest_stats.avg_out_rate / 1000000:.2f} Mbps")
            print(f"平均利用率: {latest_stats.avg_utilization:.2f}%")
        else:
            print("没有找到统计数据")

def generate_historic_traffic_data():
    """生成历史流量数据（用于演示和测试）"""
    print("\n===== 生成历史流量数据 =====")
    app = create_app()
    
    with app.app_context():
        # 查询所有设备
        devices = Device.query.filter_by(status='online').all()
        print(f"在线设备数量: {len(devices)}")
        
        if not devices:
            print("没有在线设备，请先添加或更新设备状态")
            return
        
        # 设置日期范围（过去7天）
        now = datetime.utcnow()
        days = 7
        start_date = now - timedelta(days=days)
        
        # 创建历史数据
        total_records = 0
        
        for device in devices:
            print(f"正在为设备 {device.name} (ID: {device.id}) 生成历史数据...")
            
            # 每台设备的接口
            interfaces = ["GigabitEthernet0/0", "GigabitEthernet0/1", "GigabitEthernet1/0", "Loopback0"]
            
            # 为每一天生成数据
            for day in range(days):
                # 日期
                date = start_date + timedelta(days=day)
                
                # 每天生成24小时的数据，每小时5条记录
                for hour in range(24):
                    # 设置时间
                    time_point = date + timedelta(hours=hour)
                    
                    # 为每个时间点生成5条记录（每12分钟一条）
                    for minute in range(0, 60, 12):
                        timestamp = time_point + timedelta(minutes=minute)
                        
                        # 为每个接口生成数据
                        for interface in interfaces:
                            # 根据一天中的时间生成不同的流量模式
                            time_factor = 1.0
                            
                            # 工作时间（9-18点）流量较高
                            if 9 <= hour <= 18:
                                time_factor = 1.5 + random.random() * 0.5
                            # 晚上（19-23点）流量中等
                            elif 19 <= hour <= 23:
                                time_factor = 1.0 + random.random() * 0.3
                            # 凌晨（0-8点）流量较低
                            else:
                                time_factor = 0.3 + random.random() * 0.2
                            
                            # 带宽（bps）：100Mbps, 1Gbps等
                            bandwidth = random.choice([100000000, 1000000000])
                            
                            # 入口和出口流量（字节）：随机生成
                            in_octets = int(random.uniform(0.1, 0.8) * bandwidth / 8 * 5 * time_factor)
                            out_octets = int(random.uniform(0.1, 0.8) * bandwidth / 8 * 5 * time_factor)
                            
                            # 数据包数：根据流量估算
                            in_packets = int(in_octets / random.uniform(100, 1500))
                            out_packets = int(out_octets / random.uniform(100, 1500))
                            
                            # 错误数：很少，随机生成
                            in_errors = random.randint(0, 5)
                            out_errors = random.randint(0, 5)
                            
                            # 计算入站和出站速率（bps）
                            in_rate = in_octets * 8 / 5
                            out_rate = out_octets * 8 / 5
                            
                            # 计算最大流量速率（bps）
                            max_rate = max(in_rate, out_rate)
                            
                            # 带宽利用率（百分比）
                            utilization = min(100, (max_rate / bandwidth) * 100)
                            
                            # 创建流量数据记录
                            traffic = Traffic(
                                device_id=device.id,
                                interface=interface,
                                in_octets=in_octets,
                                out_octets=out_octets,
                                in_packets=in_packets,
                                out_packets=out_packets,
                                in_errors=in_errors,
                                out_errors=out_errors,
                                bandwidth=bandwidth,
                                utilization=utilization,
                                timestamp=timestamp
                            )
                            
                            db.session.add(traffic)
                            total_records += 1
                            
                            # 每1000条记录提交一次，避免事务过大
                            if total_records % 1000 == 0:
                                db.session.commit()
                                print(f"已生成 {total_records} 条历史流量记录...")
        
        # 提交剩余记录
        db.session.commit()
        print(f"历史流量数据生成完成，共生成 {total_records} 条记录")
        
        # 处理统计数据
        print("正在生成统计数据...")
        for day in range(days):
            # 修改当前时间，以便生成每一天的统计数据
            app.config['TESTING_DATE'] = start_date + timedelta(days=day)
            # 处理流量统计
            process_traffic_stats()
        
        # 处理每日统计
        process_daily_stats()
        print("统计数据生成完成")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='流量监控系统测试脚本')
    parser.add_argument('--collect', action='store_true', help='测试流量收集功能')
    parser.add_argument('--process', action='store_true', help='测试流量统计处理功能')
    parser.add_argument('--generate', action='store_true', help='生成历史流量数据')
    parser.add_argument('--all', action='store_true', help='执行所有测试')
    
    args = parser.parse_args()
    
    # 如果没有指定参数，显示帮助信息
    if not (args.collect or args.process or args.generate or args.all):
        parser.print_help()
    else:
        # 执行测试
        if args.collect or args.all:
            test_traffic_collection()
        
        if args.process or args.all:
            test_traffic_stats_processing()
        
        if args.generate or args.all:
            generate_historic_traffic_data() 