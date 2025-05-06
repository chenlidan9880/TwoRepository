from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash
# 从app导入自定义login_required装饰器
from app import login_required, db
from app.models.terminal import Terminal
from app.models.device import Device
from app import db
from datetime import datetime, timedelta
from sqlalchemy import or_
from app.utils.terminal_identifier import identify_terminal, create_or_update_terminal, update_terminal_info, parse_user_agent
from app.utils.forms import TerminalForm

# 创建蓝图
terminal = Blueprint('terminal', __name__, url_prefix='/terminal')

@terminal.route('/')
@login_required
def index():
    """终端设备页面"""
    # 获取统计数据
    total = Terminal.query.count()
    online = Terminal.query.filter_by(is_active=True).count()
    offline = Terminal.query.filter_by(is_active=False).count()
    
    # 获取设备类型统计
    device_types = db.session.query(
        Terminal.device_type, db.func.count(Terminal.id)
    ).group_by(Terminal.device_type).all()
    
    # 获取位置统计
    locations = db.session.query(
        Terminal.location, db.func.count(Terminal.id)
    ).filter(Terminal.location != None, Terminal.location != '').group_by(Terminal.location).all()
    
    # 构建stats字典
    stats = {
        'total': total,
        'online': online,
        'offline': offline,
        'device_types': device_types,
        'locations': locations
    }
    
    # 获取请求参数用于过滤
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    device_type = request.args.get('device_type', '')
    location = request.args.get('location', '')
    
    # 查询终端列表
    query = Terminal.query
    
    # 应用搜索条件
    if search:
        query = query.filter(or_(
            Terminal.hostname.contains(search),
            Terminal.ip_address.contains(search),
            Terminal.mac_address.contains(search)
        ))
    
    # 应用状态过滤
    if status:
        if status == 'online':
            query = query.filter(Terminal.is_active == True)
        else:
            query = query.filter(Terminal.is_active == False)
    
    # 应用设备类型过滤
    if device_type:
        query = query.filter(Terminal.device_type == device_type)
    
    # 应用位置过滤
    if location:
        query = query.filter(Terminal.location == location)
    
    # 按最后活动时间降序排序
    query = query.order_by(Terminal.last_seen.desc())
    
    # 分页
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = query.paginate(page=page, per_page=per_page)
    terminals = pagination.items
    
    return render_template(
        'terminal/index.html', 
        title='终端设备管理',
        stats=stats,
        terminals=terminals,
        pagination=pagination,
        search=search,
        status=status,
        device_type=device_type,
        location=location
    )


@terminal.route('/<int:id>')
@login_required
def view(id):
    """查看终端设备详情"""
    terminal = Terminal.query.get_or_404(id)
    connected_device = terminal.connected_device
    return render_template('terminal/view.html', title='终端设备详情', terminal=terminal, connected_device=connected_device)


@terminal.route('/api/list')
@login_required
def api_list():
    """获取终端设备列表API，支持分页和查询"""
    # 获取查询参数
    device_type = request.args.get('device_type', type=str)
    os_type = request.args.get('os_type', type=str)
    status = request.args.get('status', type=str)  # 'online', 'offline'
    location = request.args.get('location', type=str)
    time_range = request.args.get('time_range', type=int)  # 过去多少小时的活动
    connected_device_id = request.args.get('connected_device_id', type=int)  # 按网络设备ID过滤
    
    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # 构建查询
    query = Terminal.query
    
    # 应用过滤条件
    if device_type:
        query = query.filter(Terminal.device_type == device_type)
    
    if os_type:
        query = query.filter(Terminal.os_type == os_type)
    
    if status:
        if status == 'online':
            query = query.filter(Terminal.is_active == True)
        else:
            query = query.filter(Terminal.is_active == False)
    
    if time_range:
        cutoff_time = datetime.utcnow() - timedelta(hours=time_range)
        query = query.filter(Terminal.last_seen >= cutoff_time)
        
    if connected_device_id:
        query = query.filter(Terminal.connected_device_id == connected_device_id)
    
    # 按最后活动时间降序排序
    query = query.order_by(Terminal.last_seen.desc())
    
    # 执行分页查询
    pagination = query.paginate(page=page, per_page=per_page)
    terminals = pagination.items
    
    # 准备分页元数据
    meta = {
        'page': page,
        'per_page': per_page,
        'total': pagination.total,
        'pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    }
    
    # 格式化数据返回
    result = {
        'terminals': [terminal.to_dict() for terminal in terminals],
        'meta': meta
    }
    
    return jsonify(result)


@terminal.route('/api/stats')
@login_required
def api_stats():
    """获取终端设备统计信息API"""
    total = Terminal.query.count()
    active = Terminal.query.filter_by(is_active=True).count()
    inactive = Terminal.query.filter_by(is_active=False).count()
    
    # 按设备类型统计
    device_types = db.session.query(
        Terminal.device_type, db.func.count(Terminal.id)
    ).group_by(Terminal.device_type).all()
    
    device_type_stats = {dt[0]: dt[1] for dt in device_types}
    
    # 按操作系统统计
    os_types = db.session.query(
        Terminal.os_type, db.func.count(Terminal.id)
    ).group_by(Terminal.os_type).all()
    
    os_type_stats = {os[0]: os[1] for os in os_types}
    
    # 按连接设备统计
    device_connections = db.session.query(
        Terminal.connected_device_id, db.func.count(Terminal.id)
    ).filter(Terminal.connected_device_id != None).group_by(Terminal.connected_device_id).all()
    
    device_connection_stats = {str(dc[0]): dc[1] for dc in device_connections}
    not_connected = Terminal.query.filter(Terminal.connected_device_id == None).count()
    
    if not_connected > 0:
        device_connection_stats['not_connected'] = not_connected
    
    # 构建并返回统计数据
    stats = {
        'total': total,
        'active': active,
        'inactive': inactive,
        'device_types': device_type_stats,
        'os_types': os_type_stats,
        'device_connections': device_connection_stats
    }
    
    return jsonify(stats)


@terminal.route('/<int:id>/assign_device', methods=['POST'])
@login_required
def assign_device(id):
    """将终端分配给网络设备"""
    terminal = Terminal.query.get_or_404(id)
    device_id = request.form.get('device_id', type=int)
    
    # 验证设备ID
    if device_id:
        device = Device.query.get(device_id)
        if not device:
            flash('无效的设备ID', 'danger')
            return redirect(url_for('terminal.view', id=id))
        
        terminal.connected_device_id = device_id
    else:
        # 如果没有指定设备ID，解除与当前设备的关联
        terminal.connected_device_id = None
    
    db.session.commit()
    flash('终端设备关联已更新', 'success')
    return redirect(url_for('terminal.view', id=id))


@terminal.route('/api/devices')
@login_required
def api_devices():
    """获取所有可用网络设备列表，用于终端设备关联"""
    devices = Device.query.order_by(Device.name).all()
    return jsonify([{'id': d.id, 'name': d.name, 'device_type': d.device_type} for d in devices])


@terminal.route('/api/<int:id>')
@login_required
def get_terminal(id):
    """获取单个终端设备详情API"""
    terminal = Terminal.query.get_or_404(id)
    return jsonify(terminal.to_dict())


@terminal.route('/api/<int:id>', methods=['PUT'])
@login_required
def update_terminal(id):
    """更新终端设备API"""
    terminal = Terminal.query.get_or_404(id)
    data = request.json
    
    # 更新基本信息
    for field in ['hostname', 'device_type', 'os_type', 'location']:
        if field in data:
            setattr(terminal, field, data[field])
    
    # 处理状态信息
    if 'status' in data:
        terminal.is_active = (data['status'] == 'online')
    elif 'is_active' in data:
        terminal.is_active = data['is_active']
    
    # 处理设备关联
    if 'connected_device_id' in data and data['connected_device_id']:
        device = Device.query.get(data['connected_device_id'])
        if device:
            terminal.connected_device_id = device.id
    elif 'connected_device_id' in data and data['connected_device_id'] is None:
        terminal.connected_device_id = None
    
    # 处理连接信息
    for field in ['port_number', 'vlan_id', 'connection_type']:
        if field in data:
            setattr(terminal, field, data[field])
    
    # 更新时间
    terminal.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({'status': 'success', 'message': '终端设备已更新'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 400


@terminal.route('/api/<int:id>', methods=['DELETE'])
@login_required
def delete_terminal(id):
    """删除终端设备API"""
    terminal = Terminal.query.get_or_404(id)
    
    try:
        db.session.delete(terminal)
        db.session.commit()
        return jsonify({'status': 'success', 'message': '终端设备已删除'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 400


@terminal.route('/discover_all', methods=['POST'])
@login_required
def discover_all():
    """手动触发全网终端设备发现"""
    try:
        from app.utils.terminal_identifier import schedule_terminal_discovery
        result = schedule_terminal_discovery()
        flash(f'终端设备发现完成，发现 {result.get("discovered", 0)} 个设备，{result.get("offline", 0)} 个设备离线', 'success')
    except Exception as e:
        flash(f'终端设备发现失败: {str(e)}', 'danger')
    
    return redirect(url_for('terminal.index'))


@terminal.route('/identify_device', methods=['POST'])
@login_required
def identify_device():
    """通过用户代理字符串识别设备信息"""
    user_agent = request.form.get('user_agent', '')
    mac_address = request.form.get('mac_address', '')
    
    if not user_agent and not mac_address:
        return jsonify({'error': '缺少必要的识别信息'}), 400
    
    terminal_data = {}
    if user_agent:
        terminal_data['user_agent'] = user_agent
    if mac_address:
        terminal_data['mac_address'] = mac_address
    
    # 识别设备信息
    identified_info = identify_terminal(terminal_data)
    
    return jsonify({
        'device_type': identified_info.get('device_type'),
        'os_type': identified_info.get('os_type'),
        'vendor': identified_info.get('vendor'),
        'browser': identified_info.get('browser')
    }) 