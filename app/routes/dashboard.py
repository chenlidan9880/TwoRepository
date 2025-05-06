#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
高级仪表盘路由模块

提供交互式仪表盘展示系统核心指标和监控数据。
"""

from flask import Blueprint, render_template, jsonify, request, current_app
from app import db
from app.models.device import Device
from app.models.terminal import Terminal
from app.models.traffic import Traffic
from app.models.alert import Alert
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
import random
import json

# 创建蓝图
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
def index():
    """高级仪表盘主页"""
    return render_template('dashboard/index.html')

@dashboard_bp.route('/api/statistics')
def get_statistics():
    """获取系统整体统计数据"""
    # 设备统计
    device_count = Device.query.count()
    online_device_count = Device.query.filter_by(status='online').count()
    
    # 设备类型统计
    device_types = db.session.query(
        Device.device_type, 
        func.count(Device.id).label('count')
    ).group_by(Device.device_type).all()
    
    device_type_data = [{'name': d_type, 'value': count} for d_type, count in device_types]
    
    # 终端统计
    terminal_count = Terminal.query.count()
    # 最近24小时有流量记录的终端被视为活跃
    last_24h = datetime.now() - timedelta(hours=24)
    active_terminal_ids = db.session.query(Traffic.terminal_id).filter(
        Traffic.timestamp > last_24h
    ).distinct().all()
    active_terminal_count = len(active_terminal_ids)
    
    # 终端类型统计
    terminal_types = db.session.query(
        Terminal.device_type, 
        func.count(Terminal.id).label('count')
    ).group_by(Terminal.device_type).all()
    
    terminal_type_data = [{'name': t_type, 'value': count} for t_type, count in terminal_types]
    
    # 告警统计
    alert_count = Alert.query.count()
    critical_alert_count = Alert.query.filter_by(severity='critical').count()
    
    # 流量统计
    traffic_count = Traffic.query.filter(Traffic.timestamp > last_24h).count()
    
    # 返回结果
    return jsonify({
        'device': {
            'total': device_count,
            'online': online_device_count,
            'types': device_type_data
        },
        'terminal': {
            'total': terminal_count,
            'active': active_terminal_count,
            'types': terminal_type_data
        },
        'alert': {
            'total': alert_count,
            'critical': critical_alert_count
        },
        'traffic': {
            'last_24h': traffic_count
        }
    })

@dashboard_bp.route('/api/traffic-trend')
def get_traffic_trend():
    """获取流量趋势数据"""
    range_param = request.args.get('range', 'day')
    device_id = request.args.get('device_id')
    
    # 确定时间范围
    end_time = datetime.now()
    if range_param == 'hour':
        start_time = end_time - timedelta(hours=1)
        interval = timedelta(minutes=5)
        format_str = '%H:%M'
    elif range_param == 'day':
        start_time = end_time - timedelta(days=1)
        interval = timedelta(hours=1)
        format_str = '%H:00'
    elif range_param == 'week':
        start_time = end_time - timedelta(days=7)
        interval = timedelta(days=1)
        format_str = '%m-%d'
    elif range_param == 'month':
        start_time = end_time - timedelta(days=30)
        interval = timedelta(days=1)
        format_str = '%m-%d'
    else:
        return jsonify({'error': '无效的时间范围参数'}), 400
    
    # 生成时间点
    current_time = start_time
    time_points = []
    while current_time <= end_time:
        time_points.append(current_time)
        current_time += interval
    
    # 查询限制条件
    filters = [Traffic.timestamp.between(start_time, end_time)]
    if device_id:
        filters.append(Traffic.device_id == device_id)
    
    # 查询流量数据
    # 注意：这里简化了查询，实际项目中应该根据时间范围进行聚合
    traffic_data = Traffic.query.filter(*filters).all()
    
    # 将流量数据按时间点汇总
    result = []
    for i, time_point in enumerate(time_points):
        next_time = time_points[i+1] if i+1 < len(time_points) else end_time
        
        # 找出该时间段的流量记录
        period_traffic = [t for t in traffic_data if time_point <= t.timestamp < next_time]
        
        # 计算该时间段的平均流量
        if period_traffic:
            in_rate = sum(t.in_bytes for t in period_traffic) / len(period_traffic)
            out_rate = sum(t.out_bytes for t in period_traffic) / len(period_traffic)
        else:
            # 如果没有数据，生成模拟数据
            base_in = random.randint(500000, 1500000)  # 基础入站流量
            base_out = random.randint(300000, 1000000)  # 基础出站流量
            
            # 为不同时间段设置不同的流量模式
            hour = time_point.hour
            if 9 <= hour < 12 or 14 <= hour < 18:  # 工作时间
                factor = 1.5
            elif 12 <= hour < 14:  # 午休时间
                factor = 0.8
            elif 18 <= hour < 22:  # 晚间时间
                factor = 1.2
            else:  # 凌晨时间
                factor = 0.5
            
            in_rate = base_in * factor
            out_rate = base_out * factor
        
        result.append({
            'time': time_point.strftime(format_str),
            'in_rate': round(in_rate),
            'out_rate': round(out_rate)
        })
    
    return jsonify(result)

@dashboard_bp.route('/api/location-statistics')
def get_location_statistics():
    """获取位置统计数据"""
    # 获取所有位置
    locations = db.session.query(Device.location).distinct().all()
    location_list = [loc[0] for loc in locations]
    
    # 准备结果
    result = []
    for location in location_list:
        # 获取该位置的设备数
        device_count = Device.query.filter_by(location=location).count()
        
        # 获取该位置设备连接的终端数
        location_devices = Device.query.filter_by(location=location).all()
        device_ids = [device.id for device in location_devices]
        
        terminal_count = Terminal.query.filter(Terminal.connected_device_id.in_(device_ids)).count() if device_ids else 0
        
        # 生成该位置的流量数据（模拟数据）
        # 在实际应用中，应该从Traffic表中查询
        in_traffic = random.randint(20, 100)
        out_traffic = random.randint(10, 80)
        
        result.append({
            'location': location,
            'device_count': device_count,
            'terminal_count': terminal_count,
            'in_traffic': in_traffic,
            'out_traffic': out_traffic
        })
    
    return jsonify(result)

@dashboard_bp.route('/api/top-terminals')
def get_top_terminals():
    """获取流量最高的终端设备"""
    limit = int(request.args.get('limit', 10))
    
    # 获取最近24小时的数据
    last_24h = datetime.now() - timedelta(hours=24)
    
    # 聚合每个终端的流量
    # 注意：这里简化了查询，实际项目中应按终端ID聚合并计算总流量
    traffic_data = Traffic.query.filter(Traffic.timestamp > last_24h).all()
    
    # 按终端ID汇总流量
    terminal_traffic = {}
    for traffic in traffic_data:
        if traffic.terminal_id not in terminal_traffic:
            terminal_traffic[traffic.terminal_id] = {
                'in_traffic': 0,
                'out_traffic': 0
            }
        terminal_traffic[traffic.terminal_id]['in_traffic'] += traffic.in_bytes
        terminal_traffic[traffic.terminal_id]['out_traffic'] += traffic.out_bytes
    
    # 按总流量排序
    sorted_terminals = sorted(
        terminal_traffic.items(),
        key=lambda x: x[1]['in_traffic'] + x[1]['out_traffic'],
        reverse=True
    )[:limit]
    
    # 查询终端详细信息
    result = []
    for terminal_id, traffic_info in sorted_terminals:
        terminal = Terminal.query.get(terminal_id)
        if terminal:
            # 获取连接的设备位置
            device = Device.query.get(terminal.connected_device_id)
            location = device.location if device else '未知'
            
            result.append({
                'id': terminal.id,
                'hostname': terminal.hostname,
                'ip_address': terminal.ip_address,
                'mac_address': terminal.mac_address,
                'device_type': terminal.device_type,
                'os_type': terminal.os_type,
                'location': location,
                'in_traffic': traffic_info['in_traffic'],
                'out_traffic': traffic_info['out_traffic']
            })
    
    return jsonify(result) 