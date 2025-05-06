"""
热力图控制器模块

负责处理流量热力图相关的请求，提供热力图数据API和页面渲染。
"""

from flask import Blueprint, render_template, jsonify, request
from app import login_required, db
from app.models.terminal import Terminal
from app.utils.visualization import get_heatmap_data, get_traffic_trend, get_terminal_distribution
from datetime import datetime, timedelta
import json
import random

# 创建蓝图
heatmap = Blueprint('heatmap', __name__, url_prefix='/heatmap')

@heatmap.route('/')
@login_required
def index():
    """渲染热力图页面"""
    return render_template('heatmap/index.html')

@heatmap.route('/data')
@login_required
def heatmap_data():
    """提供热力图数据API"""
    # 获取时间范围参数，默认为1小时
    time_range = request.args.get('time_range', 'hour')
    
    # 生成热力图数据
    data = get_heatmap_data(time_range)
    
    return jsonify(data)

@heatmap.route('/trend')
@login_required
def traffic_trend():
    """提供流量趋势数据API"""
    # 获取请求参数
    device_id = request.args.get('device_id', None)
    if device_id:
        try:
            device_id = int(device_id)
        except ValueError:
            return jsonify({'error': '设备ID必须是整数'}), 400
    
    time_range = request.args.get('time_range', 'day')
    interval = request.args.get('interval', '5min')
    
    # 生成趋势图数据
    data = get_traffic_trend(device_id, time_range, interval)
    
    return jsonify(data)

@heatmap.route('/distribution')
@login_required
def device_distribution():
    """提供设备分布数据API"""
    # 生成设备分布数据
    data = get_terminal_distribution()
    
    return jsonify(data) 