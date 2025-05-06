from flask import Blueprint, render_template, jsonify, request, current_app
from app import login_required
from app.models.terminal import Terminal
from app.models.device import Device
from app import db
from datetime import datetime

bp = Blueprint('terminal', __name__)

@bp.route('/')
@login_required
def index():
    """终端设备列表页面"""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ITEMS_PER_PAGE']
    
    # 获取查询参数
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    device_type = request.args.get('device_type', '')
    location = request.args.get('location', '')
    
    # 构建查询
    query = Terminal.query
    
    if search:
        query = query.filter(
            db.or_(
                Terminal.hostname.ilike(f'%{search}%'),
                Terminal.ip_address.ilike(f'%{search}%'),
                Terminal.mac_address.ilike(f'%{search}%')
            )
        )
    
    if status:
        # 修正为使用is_active字段
        if status == 'online':
            query = query.filter(Terminal.is_active == True)
        elif status == 'offline':
            query = query.filter(Terminal.is_active == False)
    
    if device_type:
        query = query.filter(Terminal.device_type == device_type)
    
    if location:
        query = query.filter(Terminal.location == location)
    
    # 执行分页查询
    pagination = query.order_by(Terminal.last_seen.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    terminals = pagination.items
    
    # 获取统计信息
    stats = {
        'total': Terminal.query.count(),
        'online': Terminal.query.filter_by(is_active=True).count(),
        'offline': Terminal.query.filter_by(is_active=False).count(),
        'device_types': db.session.query(Terminal.device_type, db.func.count(Terminal.id)).group_by(Terminal.device_type).all(),
        'locations': db.session.query(Terminal.location, db.func.count(Terminal.id)).group_by(Terminal.location).all()
    }
    
    return render_template('terminal/index.html',
                         terminals=terminals,
                         pagination=pagination,
                         stats=stats,
                         search=search,
                         status=status,
                         device_type=device_type,
                         location=location)

@bp.route('/<int:id>')
@login_required
def detail(id):
    """终端设备详情页面"""
    terminal = Terminal.query.get_or_404(id)
    return render_template('terminal/detail.html', terminal=terminal)

@bp.route('/api/terminals')
@login_required
def api_terminals():
    """获取终端设备列表的API"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    query = Terminal.query
    
    # 应用过滤条件
    search = request.args.get('search', '')
    if search:
        query = query.filter(
            db.or_(
                Terminal.hostname.ilike(f'%{search}%'),
                Terminal.ip_address.ilike(f'%{search}%'),
                Terminal.mac_address.ilike(f'%{search}%')
            )
        )
    
    status = request.args.get('status', '')
    if status:
        # 修正为使用is_active字段
        if status == 'online':
            query = query.filter(Terminal.is_active == True)
        elif status == 'offline':
            query = query.filter(Terminal.is_active == False)
    
    device_type = request.args.get('device_type', '')
    if device_type:
        query = query.filter(Terminal.device_type == device_type)
    
    location = request.args.get('location', '')
    if location:
        query = query.filter(Terminal.location == location)
    
    # 执行分页查询
    pagination = query.order_by(Terminal.last_seen.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'items': [terminal.to_dict() for terminal in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

@bp.route('/api/terminals/<int:id>', methods=['GET'])
@login_required
def get_terminal(id):
    """获取单个终端设备信息的API"""
    terminal = Terminal.query.get_or_404(id)
    return jsonify(terminal.to_dict())

@bp.route('/api/terminals/<int:id>', methods=['PUT'])
@login_required
def update_terminal(id):
    """更新终端设备信息的API"""
    terminal = Terminal.query.get_or_404(id)
    data = request.get_json()
    
    # 更新基本信息
    for field in ['hostname', 'device_type', 'os_type', 'location']:
        if field in data:
            setattr(terminal, field, data[field])
    
    # 更新连接信息
    if 'connected_device_id' in data and data['connected_device_id']:
        device = Device.query.get(data['connected_device_id'])
        if device:
            terminal.connected_device_id = device.id
    elif 'connected_device_id' in data and data['connected_device_id'] is None:
        terminal.connected_device_id = None
    
    if 'port_number' in data:
        terminal.port_number = data['port_number']
    
    if 'vlan_id' in data:
        terminal.vlan_id = data['vlan_id']
    
    if 'connection_type' in data:
        terminal.connection_type = data['connection_type']
    
    # 处理状态字段
    if 'status' in data:
        terminal.is_active = (data['status'] == 'online')
    elif 'is_active' in data:
        terminal.is_active = data['is_active']
    
    terminal.updated_at = datetime.now()
    
    try:
        db.session.commit()
        return jsonify({'message': '更新成功', 'terminal': terminal.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/terminals/<int:id>', methods=['DELETE'])
@login_required
def delete_terminal(id):
    """删除终端设备的API"""
    terminal = Terminal.query.get_or_404(id)
    
    try:
        db.session.delete(terminal)
        db.session.commit()
        return jsonify({'message': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/terminals/stats')
@login_required
def terminal_stats():
    """获取终端设备统计信息的API"""
    stats = {
        'total': Terminal.query.count(),
        'online': Terminal.query.filter_by(is_active=True).count(),
        'offline': Terminal.query.filter_by(is_active=False).count(),
        'device_types': db.session.query(Terminal.device_type, db.func.count(Terminal.id)).group_by(Terminal.device_type).all(),
        'locations': db.session.query(Terminal.location, db.func.count(Terminal.id)).group_by(Terminal.location).all()
    }
    return jsonify(stats)

@bp.route('/api/devices')
@login_required
def api_devices():
    """获取网络设备列表的API，供终端设备关联选择"""
    devices = Device.query.all()
    return jsonify({
        'items': [{'id': device.id, 'name': device.name} for device in devices]
    }) 