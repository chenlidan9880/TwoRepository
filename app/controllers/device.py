from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
# 从app导入自定义login_required装饰器
from app import login_required, db
from app.models.device import Device
from app.models.terminal import Terminal
from app.models.traffic import Traffic, TrafficStats
from app.utils.forms import DeviceForm
from datetime import datetime, timedelta

# 创建蓝图
device = Blueprint('device', __name__, url_prefix='/device')

@device.route('/')
@login_required
def index():
    """设备列表页面"""
    devices = Device.query.all()
    
    # 为每个设备添加连接的终端数量和紧急告警数量
    for device in devices:
        device.connected_terminals_count = Terminal.query.filter_by(connected_device_id=device.id).count()
        # 添加紧急告警数量统计
        from app.models.alert import Alert
        device.critical_alerts = Alert.query.filter_by(
            device_id=device.id, 
            severity='critical',
            is_handled=False
        ).count()
        
    return render_template('device/index.html', title='设备管理', devices=devices)


@device.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加设备"""
    form = DeviceForm()
    if form.validate_on_submit():
        device = Device(
            name=form.name.data,
            ip_address=form.ip_address.data,
            device_type=form.device_type.data,
            location=form.location.data,
            snmp_community=form.snmp_community.data,
            snmp_version=form.snmp_version.data,
            snmp_port=form.snmp_port.data,
            description=form.description.data
        )
        db.session.add(device)
        db.session.commit()
        flash('设备添加成功')
        return redirect(url_for('device.index'))
    
    return render_template('device/add.html', title='添加设备', form=form)


@device.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """编辑设备"""
    device = Device.query.get_or_404(id)
    form = DeviceForm(obj=device)
    
    if form.validate_on_submit():
        device.name = form.name.data
        device.ip_address = form.ip_address.data
        device.device_type = form.device_type.data
        device.location = form.location.data
        device.snmp_community = form.snmp_community.data
        device.snmp_version = form.snmp_version.data
        device.snmp_port = form.snmp_port.data
        device.description = form.description.data
        
        db.session.commit()
        flash('设备更新成功')
        return redirect(url_for('device.index'))
    
    return render_template('device/edit.html', title='编辑设备', form=form, device=device)


@device.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """删除设备"""
    device = Device.query.get_or_404(id)
    
    # 获取是否一并删除终端设备的选项
    delete_terminals = request.form.get('delete_terminals', '0') == '1'
    
    # 获取关联的终端设备
    connected_terminals = Terminal.query.filter_by(connected_device_id=id).all()
    terminals_count = len(connected_terminals)
    
    if delete_terminals and terminals_count > 0:
        # 删除关联终端设备以及其流量数据
        for terminal in connected_terminals:
            # 这里可以添加删除终端相关数据的逻辑，如流量记录等
            db.session.delete(terminal)
        
        db.session.flush()  # 提交终端删除但不提交事务
        flash(f'已删除设备 {device.name} 及其关联的 {terminals_count} 台终端设备')
    else:
        # 断开终端设备的连接
        for terminal in connected_terminals:
            terminal.connected_device_id = None
            terminal.port_number = None
            terminal.connection_type = None
        
        db.session.flush()  # 提交终端更新但不提交事务
        
        if terminals_count > 0:
            flash(f'已删除设备 {device.name}，并断开了 {terminals_count} 台关联终端设备的连接')
        else:
            flash(f'已删除设备 {device.name}')
    
    # 删除设备相关的流量记录
    Traffic.query.filter_by(device_id=id).delete()
    
    # 删除设备相关的流量统计
    TrafficStats.query.filter_by(device_id=id).delete()
    
    # 删除设备相关的告警
    from app.models.alert import Alert
    Alert.query.filter_by(device_id=id).delete()
    
    # 最后删除设备
    db.session.delete(device)
    
    # 提交所有更改
    db.session.commit()
    
    return redirect(url_for('device.index'))


@device.route('/<int:id>')
@login_required
def view(id):
    """查看设备详情"""
    device = Device.query.get_or_404(id)
    
    # 清理终端关联逻辑，确保终端显示正确
    try:
        # 清理悬空终端引用
        orphan_terminals = Terminal.query.filter(
            Terminal.connected_device_id == id,
            ~Terminal.id.in_(db.session.query(Terminal.id).filter(Terminal.connected_device_id == id))
        ).all()
        
        if orphan_terminals:
            for terminal in orphan_terminals:
                print(f"修复悬空终端: {terminal.id}")
                terminal.connected_device_id = None
            db.session.commit()
    except Exception as e:
        print(f"清理终端关系出错: {str(e)}")
    
    # 查询显式关联到此设备的终端
    print(f"设备ID: {id}")
    connected_terminals_query = Terminal.query.filter(Terminal.connected_device_id == id)
    connected_terminals = connected_terminals_query.all()
    terminal_count = connected_terminals_query.count()
    
    print(f"DEBUG: 设备ID: {id}, 找到 {terminal_count} 个连接的终端设备")
    for terminal in connected_terminals:
        print(f"DEBUG: 终端ID: {terminal.id}, 主机名: {terminal.hostname}, 连接设备ID: {terminal.connected_device_id}")
    
    # 查询最近24小时的流量数据，用于流量趋势图
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    
    # 获取按小时间隔的流量数据
    traffic_data = db.session.query(
        db.func.date_format(Traffic.timestamp, '%H:00').label('hour'),
        db.func.sum(Traffic.in_octets).label('in_traffic'),
        db.func.sum(Traffic.out_octets).label('out_traffic')
    ).filter(
        Traffic.device_id == id,
        Traffic.timestamp.between(start_time, end_time)
    ).group_by('hour').all()
    
    # 计算总流量、入站流量和出站流量
    total_traffic_stats = db.session.query(
        db.func.sum(Traffic.in_octets).label('in_traffic'),
        db.func.sum(Traffic.out_octets).label('out_traffic')
    ).filter(
        Traffic.device_id == id
    ).first()
    
    # 为模板准备数据
    hours = []
    in_traffic = []
    out_traffic = []
    
    # 如果有流量数据，格式化数据用于图表
    if traffic_data:
        for data in traffic_data:
            hours.append(data.hour)
            in_traffic.append(float(data.in_traffic) / (1024*1024))  # 转换为MB
            out_traffic.append(float(data.out_traffic) / (1024*1024))  # 转换为MB
    else:
        # 如果没有数据，创建模拟数据
        for i in range(24):
            hour = (datetime.utcnow() - timedelta(hours=i)).strftime('%H:00')
            hours.insert(0, hour)
            in_traffic.insert(0, 0)
            out_traffic.insert(0, 0)
    
    # 计算设备总流量信息
    in_total = 0
    out_total = 0
    total = 0
    
    if total_traffic_stats and total_traffic_stats.in_traffic and total_traffic_stats.out_traffic:
        in_total = float(total_traffic_stats.in_traffic)
        out_total = float(total_traffic_stats.out_traffic)
        total = in_total + out_total
    
    # 手动设置设备流量属性
    device.in_traffic = in_total
    device.out_traffic = out_total
    device.total_traffic = total
    
    # 追加终端数量属性
    device.terminal_count = terminal_count
    
    # 查询设备告警
    from app.models.alert import Alert
    alerts = Alert.query.filter_by(device_id=id).order_by(Alert.created_at.desc()).limit(5).all()
    
    return render_template(
        'device/view.html', 
        title=f'设备详情 - {device.name}', 
        device=device,
        hours=hours,
        in_traffic=in_traffic,
        out_traffic=out_traffic,
        connected_terminals=connected_terminals,
        alerts=alerts
    )


@device.route('/api/list')
@login_required
def api_list():
    """设备列表API"""
    devices = Device.query.all()
    return jsonify([device.to_dict() for device in devices])


@device.route('/<int:id>/terminals')
@login_required
def device_terminals(id):
    """查看设备连接的终端设备"""
    device = Device.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    pagination = Terminal.query.filter_by(connected_device_id=id).paginate(page=page, per_page=per_page)
    terminals = pagination.items
    
    return render_template('device/terminals.html', title=f'{device.name} - 连接的终端设备', 
                           device=device, terminals=terminals, pagination=pagination)


@device.route('/api/<int:id>/terminals')
@login_required
def api_device_terminals(id):
    """设备连接的终端设备API"""
    Device.query.get_or_404(id)  # 确保设备存在
    
    terminals = Terminal.query.filter_by(connected_device_id=id).all()
    return jsonify([terminal.to_dict() for terminal in terminals])


@device.route('/<int:id>/terminal/<int:terminal_id>/disconnect', methods=['POST'])
@login_required
def disconnect_terminal(id, terminal_id):
    """从设备断开终端连接"""
    device = Device.query.get_or_404(id)
    terminal = Terminal.query.get_or_404(terminal_id)
    
    if terminal.connected_device_id != id:
        flash(f'终端 {terminal.hostname} 当前未连接到设备 {device.name}', 'warning')
    else:
        terminal.connected_device_id = None
        terminal.port_number = None
        terminal.connection_type = None
        db.session.commit()
        flash(f'已断开终端 {terminal.hostname} 与设备 {device.name} 的连接', 'success')
    
    return redirect(url_for('device.device_terminals', id=id))


@device.route('/api/<int:id>/discover_terminals', methods=['POST'])
@login_required
def api_discover_terminals(id):
    """手动触发设备终端发现"""
    device = Device.query.get_or_404(id)
    
    try:
        # 导入终端发现函数
        from app.utils.terminal_identifier import discover_terminals_for_device
        
        # 执行终端发现
        discovered_count = discover_terminals_for_device(device)
        
        # 返回发现结果
        return jsonify({
            "status": "success",
            "message": f"成功发现 {discovered_count} 个终端设备",
            "discovered_count": discovered_count
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"终端发现失败: {str(e)}"
        }) 