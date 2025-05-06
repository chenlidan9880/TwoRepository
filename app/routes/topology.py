#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
网络拓扑可视化路由模块

提供网络拓扑展示和交互的路由，包括2D和3D可视化。
"""

from flask import Blueprint, render_template, jsonify, request, current_app
import json
import os
import networkx as nx
from app import db
from app.models.device import Device
from app.models.terminal import Terminal

# 创建蓝图
topology_bp = Blueprint('topology', __name__, url_prefix='/topology')

@topology_bp.route('/')
def index():
    """网络拓扑概览页面"""
    # 获取设备统计
    device_count = Device.query.count()
    router_count = Device.query.filter_by(device_type='router').count()
    switch_count = Device.query.filter_by(device_type='switch').count()
    wireless_count = Device.query.filter_by(device_type='wireless').count()
    
    # 获取终端统计
    terminal_count = Terminal.query.count()
    pc_count = Terminal.query.filter_by(device_type='PC').count()
    mobile_count = Terminal.query.filter_by(device_type='Mobile').count()
    iot_count = Terminal.query.filter_by(device_type='IoT').count()
    
    return render_template('topology/index.html',
                           device_count=device_count,
                           router_count=router_count,
                           switch_count=switch_count,
                           wireless_count=wireless_count,
                           terminal_count=terminal_count,
                           pc_count=pc_count,
                           mobile_count=mobile_count,
                           iot_count=iot_count)

@topology_bp.route('/advanced')
def advanced():
    """高级网络拓扑可视化，使用D3.js提供交互式体验"""
    return render_template('topology/advanced.html')

@topology_bp.route('/3d')
def view3d():
    """3D网络拓扑可视化，使用Three.js提供立体展示"""
    return render_template('topology/3d.html')

@topology_bp.route('/api/topology-data')
def get_topology_data():
    """获取网络拓扑数据的API"""
    try:
        # 尝试从文件加载拓扑数据
        topology_file = os.path.join(current_app.root_path, '..', 'data', 'network_topology.json')
        if os.path.exists(topology_file):
            with open(topology_file, 'r') as f:
                topology_data = json.load(f)
            return jsonify(topology_data)
        
        # 如果文件不存在，从数据库创建拓扑数据
        # 创建图结构
        G = nx.Graph()
        
        # 添加设备节点
        devices = Device.query.all()
        for device in devices:
            G.add_node(device.id, 
                       id=device.id,
                       name=device.name, 
                       type=device.device_type, 
                       ip=device.ip_address, 
                       location=device.location)
        
        # 确定设备之间的连接关系（假设核心路由器连接到汇聚交换机，汇聚交换机连接到接入设备）
        core_router = Device.query.filter_by(device_type='router').first()
        aggregation_switches = Device.query.filter(
            Device.device_type == 'switch',
            Device.name.like('%汇聚%')
        ).all()
        
        # 核心路由器连接到汇聚交换机
        if core_router:
            for switch in aggregation_switches:
                G.add_edge(core_router.id, switch.id)
        
        # 汇聚交换机连接到接入交换机
        access_devices = Device.query.filter(
            (Device.device_type == 'switch') | (Device.device_type == 'wireless'),
            ~Device.name.like('%汇聚%')
        ).all()
        
        # 根据区域关联接入设备和汇聚交换机
        for device in access_devices:
            # 查找同一区域的汇聚交换机
            related_switch = next(
                (s for s in aggregation_switches if s.location == device.location), 
                None
            )
            if related_switch:
                G.add_edge(related_switch.id, device.id)
        
        # 转换为D3.js格式
        nodes = [{'id': node_id, 'name': data.get('name', ''), 
                 'type': data.get('type', ''), 'location': data.get('location', ''),
                 'ip': data.get('ip', '')}
                for node_id, data in G.nodes(data=True)]
        
        links = [{'source': u, 'target': v} for u, v in G.edges()]
        
        result = {'nodes': nodes, 'links': links}
        return jsonify(result)
    
    except Exception as e:
        current_app.logger.error(f"获取拓扑数据时出错: {str(e)}")
        return jsonify({'error': str(e)}), 500

@topology_bp.route('/api/device-details/<int:device_id>')
def get_device_details(device_id):
    """获取设备详细信息API"""
    device = Device.query.get_or_404(device_id)
    
    # 查询连接到该设备的终端数量
    connected_terminals = Terminal.query.filter_by(connected_device_id=device_id).count()
    
    # 获取设备状态统计
    if device.device_type == 'switch' or device.device_type == 'router':
        port_count = 24  # 假设交换机/路由器有24个端口
        active_ports = min(port_count, Terminal.query.filter_by(connected_device_id=device_id).count())
        port_utilization = round((active_ports / port_count) * 100, 2) if port_count > 0 else 0
    else:  # wireless
        port_count = 0
        active_ports = 0
        port_utilization = 0
    
    return jsonify({
        'id': device.id,
        'name': device.name,
        'type': device.device_type,
        'ip_address': device.ip_address,
        'location': device.location,
        'status': device.status,
        'connected_terminals': connected_terminals,
        'port_count': port_count,
        'active_ports': active_ports,
        'port_utilization': port_utilization
    }) 