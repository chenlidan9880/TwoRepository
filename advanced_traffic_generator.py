#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
高级流量模拟模块 - 使用ARIMA和GARCH等高级统计模型生成更真实的流量数据
"""

import numpy as np
from statsmodels.tsa.arima.model import ARIMA
import statsmodels.api as sm
from arch import arch_model
import pandas as pd
import random
import os
import sys
from datetime import datetime, timedelta
from app import create_app, db
from app.models.device import Device
from app.models.terminal import Terminal
from app.models.traffic import Traffic

def setup_base_traffic_pattern(device_type):
    """根据设备类型设置基础流量模式"""
    patterns = {
        'router': {
            'bandwidth': random.randint(10000, 40000),  # 10-40 Gbps
            'base_utilization': {
                'business_hours': random.uniform(0.4, 0.8),  # 40%-80%
                'evening': random.uniform(0.3, 0.6),        # 30%-60%
                'night': random.uniform(0.1, 0.3)          # 10%-30%
            },
            'traffic_ratio': random.uniform(0.9, 1.1)  # 入站/出站流量比例
        },
        'switch': {
            'bandwidth': random.randint(1000, 10000),  # 1-10 Gbps
            'base_utilization': {
                'business_hours': random.uniform(0.3, 0.7),  # 30%-70%
                'evening': random.uniform(0.2, 0.5),        # 20%-50%
                'night': random.uniform(0.05, 0.2)         # 5%-20%
            },
            'traffic_ratio': random.uniform(0.8, 1.2)  # 入站/出站流量比例
        },
        'wireless': {
            'bandwidth': random.randint(300, 1200),  # 300-1200 Mbps
            'base_utilization': {
                'business_hours': random.uniform(0.5, 0.9),  # 50%-90%
                'evening': random.uniform(0.3, 0.7),        # 30%-70%
                'night': random.uniform(0.05, 0.3)         # 5%-30%
            },
            'traffic_ratio': random.uniform(0.7, 1.3)  # 入站/出站流量比例
        }
    }
    
    # 默认为交换机模式
    return patterns.get(device_type, patterns['switch'])

def generate_arima_trend(n_samples):
    """生成ARIMA模型的趋势数据"""
    # 简单的随机游走模型 ARIMA(1,1,0)
    np.random.seed(random.randint(1, 1000))  # 每次随机种子以增加变化性
    ar_params = np.array([0.8])
    ma_params = np.array([0.2])
    ar = np.r_[1, -ar_params]
    ma = np.r_[1, ma_params]
    
    arma_process = sm.tsa.ArmaProcess(ar, ma)
    y = arma_process.generate_sample(n_samples)
    
    # 归一化到0-1之间
    y = (y - np.min(y)) / (np.max(y) - np.min(y) + 1e-10)
    return y

def generate_garch_volatility(n_samples):
    """使用GARCH模型生成波动率数据"""
    # 生成随机噪声
    np.random.seed(random.randint(1, 1000))  # 每次随机种子以增加变化性
    returns = np.random.normal(0, 1, max(n_samples+200, 1000))
    
    # 使用GARCH模型
    model = arch_model(returns, vol='Garch', p=1, q=1)
    try:
        model_fit = model.fit(disp='off')
        
        # 获取预测波动率
        forecasts = model_fit.forecast(horizon=1)
        volatility = np.sqrt(forecasts.variance.values[-n_samples:].flatten())
        
        # 归一化到0-1之间
        volatility = (volatility - np.min(volatility)) / (np.max(volatility) - np.min(volatility) + 1e-10)
        return volatility
    except Exception as e:
        print(f"GARCH模型生成波动率出错: {str(e)}")
        # 备用方案：使用简单的随机过程
        np.random.seed(random.randint(1, 1000))
        vol = np.abs(np.cumsum(np.random.normal(0, 0.1, n_samples)))
        vol = (vol - np.min(vol)) / (np.max(vol) - np.min(vol) + 1e-10)
        return vol

def generate_terminal_traffic_pattern(device_type):
    """为不同类型的终端设备生成流量模式"""
    patterns = {
        'PC': {
            'in_traffic': random.randint(500000000, 5000000000),  # 500MB-5GB
            'out_traffic': random.randint(100000000, 1000000000),  # 100MB-1GB
            'bandwidth_usage': random.uniform(0.1, 0.5)  # 10%-50%利用率
        },
        'Mobile': {
            'in_traffic': random.randint(100000000, 2000000000),  # 100MB-2GB
            'out_traffic': random.randint(50000000, 500000000),  # 50MB-500MB
            'bandwidth_usage': random.uniform(0.05, 0.3)  # 5%-30%利用率
        },
        'IoT': {
            'in_traffic': random.randint(10000000, 100000000),  # 10MB-100MB
            'out_traffic': random.randint(1000000, 10000000),  # 1MB-10MB
            'bandwidth_usage': random.uniform(0.01, 0.1)  # 1%-10%利用率
        }
    }
    
    # 默认为PC类型
    return patterns.get(device_type, patterns['PC'])

def update_terminal_traffic(terminal, traffic_pattern):
    """更新终端设备的流量统计"""
    # 应用一些随机波动
    in_traffic = int(traffic_pattern['in_traffic'] * random.uniform(0.8, 1.2))
    out_traffic = int(traffic_pattern['out_traffic'] * random.uniform(0.8, 1.2))
    bandwidth_usage = traffic_pattern['bandwidth_usage'] * random.uniform(0.9, 1.1)
    
    # 更新终端流量统计
    terminal.in_traffic = in_traffic
    terminal.out_traffic = out_traffic
    terminal.bandwidth_usage = bandwidth_usage
    terminal.last_seen = datetime.now() - timedelta(minutes=random.randint(0, 120))
    
    # 随机设置在线状态
    terminal.is_active = random.random() > 0.2  # 80%概率在线
    
    db.session.add(terminal)

def generate_device_traffic(device, start_time, end_time, samples_per_hour, 
                           base_traffic, trend_data, volatility_data):
    """为设备生成流量数据"""
    current_time = start_time
    traffic_data_list = []
    sample_interval = timedelta(hours=1) / samples_per_hour
    
    # 创建设备流量随时间波动的周期性模式（工作日/周末）
    weekday_multiplier = np.array([0.7, 0.8, 1.0, 1.2, 1.1, 0.9, 0.6])  # 周一到周日
    
    # 随机生成1-3个接口名称
    interfaces = []
    if device.device_type == 'router':
        interfaces = [f"GigabitEthernet{random.randint(0,2)}/{random.randint(0,1)}" for _ in range(3)]
    elif device.device_type == 'switch':
        interfaces = [f"GigabitEthernet0/{random.randint(1,24)}" for _ in range(3)]
    else:  # wireless
        interfaces = ["GigabitEthernet0/1", "Wireless1/0"]
    
    i = 0
    while current_time <= end_time:
        # 工作日/周末乘数
        day_of_week = current_time.weekday()
        day_multiplier = weekday_multiplier[day_of_week]
        
        # 获取一天中的时间段
        hour = current_time.hour
        if 8 <= hour < 18:  # 工作时间
            base_util = base_traffic['base_utilization']['business_hours'] * day_multiplier
        elif 18 <= hour < 23:  # 晚上
            base_util = base_traffic['base_utilization']['evening'] * day_multiplier
        else:  # 夜间
            base_util = base_traffic['base_utilization']['night'] * day_multiplier
        
        # 将ARIMA趋势和GARCH波动率合并到基础利用率
        if i < len(trend_data) and i < len(volatility_data):
            trend_component = trend_data[i] * 0.2
            volatility_component = volatility_data[i] * 0.3
            
            # 计算最终利用率
            utilization = base_util + trend_component - volatility_component
            utilization = max(0.01, min(0.95, utilization))  # 确保在0.01-0.95之间
        else:
            utilization = base_util
        
        # 计算流量（字节/秒）
        bandwidth_bps = base_traffic['bandwidth'] * 1000000  # 转为bps
        total_traffic_bps = bandwidth_bps * utilization
        
        # 应用流量比例计算入站和出站
        in_ratio = base_traffic['traffic_ratio']
        in_traffic_bps = total_traffic_bps / (1 + in_ratio)
        out_traffic_bps = total_traffic_bps - in_traffic_bps
        
        # 转换为字节/秒
        in_octets = int(in_traffic_bps / 8)
        out_octets = int(out_traffic_bps / 8)
        
        # 生成数据包数（假设平均数据包大小为500字节）
        avg_packet_size = 500
        in_packets = int(in_octets / avg_packet_size) if in_octets > 0 else 1
        out_packets = int(out_octets / avg_packet_size) if out_octets > 0 else 1
        
        # 生成错误率（基于利用率增加）
        error_factor = 0.0001 + (utilization ** 2) * 0.001  # 高利用率时错误率上升
        in_errors = int(in_packets * error_factor * random.uniform(0.5, 1.5))
        out_errors = int(out_packets * error_factor * random.uniform(0.5, 1.5))
        
        # 对每个接口创建流量记录
        for interface in interfaces:
            # 每个接口有轻微的流量变化
            interface_factor = random.uniform(0.9, 1.1)
            
            traffic = Traffic(
                device_id=device.id,
                interface=interface,
                in_octets=int(in_octets * interface_factor),
                out_octets=int(out_octets * interface_factor),
                in_packets=int(in_packets * interface_factor),
                out_packets=int(out_packets * interface_factor),
                in_errors=int(in_errors * interface_factor),
                out_errors=int(out_errors * interface_factor),
                bandwidth=bandwidth_bps,
                utilization=utilization * 100,  # 转换为百分比
                timestamp=current_time
            )
            
            traffic_data_list.append(traffic)
        
        # 增加时间和索引
        current_time += sample_interval
        i += 1
        
        # 批量提交，避免内存问题
        if len(traffic_data_list) >= 1000:
            db.session.add_all(traffic_data_list)
            db.session.commit()
            traffic_data_list = []
    
    # 提交剩余记录
    if traffic_data_list:
        db.session.add_all(traffic_data_list)
        db.session.commit()

def generate_advanced_traffic(days=7, samples_per_hour=12, clear_existing=True):
    """生成基于复杂统计模型的高级流量数据
    
    使用ARIMA和GARCH模型生成符合真实网络特性的流量波动
    """
    app = create_app()
    with app.app_context():
        # 获取所有设备
        devices = Device.query.all()
        terminals = Terminal.query.all()
        
        if not devices:
            print("没有设备，请先生成网络拓扑")
            return False
            
        print(f"开始为{len(devices)}个设备和{len(terminals)}个终端生成{days}天的高级模拟流量数据...")
        
        # 删除现有的流量数据
        if clear_existing:
            try:
                print("删除现有流量数据...")
                Traffic.query.delete()
                db.session.commit()
            except Exception as e:
                print(f"删除流量数据出错: {str(e)}")
                db.session.rollback()
        
        # 设置开始和结束时间
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # 为每个设备生成更复杂的流量模式
        for device in devices:
            print(f"为设备 {device.name} 生成高级流量数据...")
            
            # 基于设备类型确定基础流量特征
            base_traffic = setup_base_traffic_pattern(device.device_type)
            
            # 生成ARIMA预测的基础趋势
            n_samples = samples_per_hour * 24 * days
            trend_data = generate_arima_trend(n_samples)
            
            # 生成GARCH波动率模拟的噪声
            volatility_data = generate_garch_volatility(n_samples)
            
            # 为设备生成流量数据
            generate_device_traffic(device, start_time, end_time, 
                                   samples_per_hour, base_traffic, 
                                   trend_data, volatility_data)
            
        # 为终端设备生成流量数据
        print("为终端设备更新流量统计...")
        for terminal in terminals:
            # 根据终端类型定义流量模式
            terminal_traffic = generate_terminal_traffic_pattern(terminal.device_type)
            
            # 更新终端流量统计
            update_terminal_traffic(terminal, terminal_traffic)
        
        # 提交所有更改
        db.session.commit()
        
        # 总结
        total_records = Traffic.query.count()
        print(f"完成高级模拟数据生成，共生成 {total_records} 条流量记录")
        return True

if __name__ == "__main__":
    try:
        # 默认生成7天的数据，每5分钟一个样本点
        days = 7
        samples_per_hour = 12  # 每5分钟一个样本
        clear_existing = True
        
        # 如果提供了参数，则使用参数
        if len(sys.argv) > 1:
            days = int(sys.argv[1])
        if len(sys.argv) > 2:
            samples_per_hour = int(sys.argv[2])
        if len(sys.argv) > 3:
            clear_existing = sys.argv[3].lower() != 'false' and sys.argv[3] != '0'
        
        print(f"生成流量数据: {days}天, 每小时{samples_per_hour}个样本, 清除现有数据: {clear_existing}")
        generate_advanced_traffic(days, samples_per_hour, clear_existing)
        print("高级流量数据生成完成！")
    except Exception as e:
        print(f"生成模拟数据时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 