from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, g
from app import db, login_required
from app.models.alert import Alert
from app.models.device import Device
from datetime import datetime, timedelta
from sqlalchemy import or_

# 创建蓝图
alert = Blueprint('alert', __name__, url_prefix='/alert')

@alert.route('/')
@login_required
def index():
    """告警页面"""
    # 获取所有设备供查询表单使用
    devices = Device.query.all()
    return render_template('alert/index.html', title='告警管理', devices=devices)
# 渲染模板文件 alert/index.html


@alert.route('/api/list')
@login_required
def api_list():
    """获取告警列表API，支持分页和查询"""
    # 获取查询参数
    device_id = request.args.get('device_id', type=int)
    alert_type = request.args.get('alert_type', type=str)
    severity = request.args.get('severity', type=str)
    status = request.args.get('status', type=str)  # 'handled', 'unhandled', 'read', 'unread'
    time_range = request.args.get('time_range', type=int)  # 过去多少小时的数据
    search_term = request.args.get('search', type=str)
    
    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # 构建查询
    query = Alert.query
    
    # 应用过滤条件
    if device_id:
        query = query.filter(Alert.device_id == device_id)
    
    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)
    
    if severity:
        query = query.filter(Alert.severity == severity)
    
    if status:
        if status == 'handled':
            query = query.filter(Alert.is_handled == True)
        elif status == 'unhandled':
            query = query.filter(Alert.is_handled == False)
        elif status == 'read':
            query = query.filter(Alert.is_read == True)
        elif status == 'unread':
            query = query.filter(Alert.is_read == False)
    
    if time_range:
        cutoff_time = datetime.utcnow() - timedelta(hours=time_range)
        query = query.filter(Alert.created_at >= cutoff_time)
    
    if search_term:
        query = query.filter(
            or_(
                Alert.title.ilike(f'%{search_term}%'),
                Alert.message.ilike(f'%{search_term}%')
            )
        )
    
    # 按时间降序排序
    query = query.order_by(Alert.created_at.desc())
    
    # 执行分页查询
    pagination = query.paginate(page=page, per_page=per_page)
    alerts = pagination.items
    
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
        'alerts': [alert.to_dict() for alert in alerts],
        'meta': meta
    }
    
    return jsonify(result)


@alert.route('/api/count')
@login_required
def api_count():
    """获取告警统计信息API"""
    total = Alert.query.count()
    unhandled = Alert.query.filter_by(is_handled=False).count()
    critical = Alert.query.filter_by(severity='critical', is_handled=False).count()
    warning = Alert.query.filter_by(severity='warning', is_handled=False).count()
    info = Alert.query.filter_by(severity='info', is_handled=False).count()
    
    return jsonify({
        'total': total,
        'unhandled': unhandled,
        'critical': critical,
        'warning': warning,
        'info': info
    })


@alert.route('/api/stats')
@login_required
def api_stats():
    """获取更详细的告警统计数据API，用于数据可视化"""
    # 获取时间范围参数，默认为过去7天
    days = request.args.get('days', 7, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # 按严重程度统计每天的告警数量
    daily_data = []
    for i in range(days):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        day_str = day_start.strftime('%Y-%m-%d')
        
        critical_count = Alert.query.filter(
            Alert.severity == 'critical',
            Alert.created_at >= day_start,
            Alert.created_at < day_end
        ).count()
        
        warning_count = Alert.query.filter(
            Alert.severity == 'warning',
            Alert.created_at >= day_start,
            Alert.created_at < day_end
        ).count()
        
        info_count = Alert.query.filter(
            Alert.severity == 'info',
            Alert.created_at >= day_start,
            Alert.created_at < day_end
        ).count()
        
        daily_data.append({
            'date': day_str,
            'critical': critical_count,
            'warning': warning_count,
            'info': info_count,
            'total': critical_count + warning_count + info_count
        })
    
    # 按告警类型统计
    alert_types = db.session.query(Alert.alert_type, db.func.count(Alert.id)).\
        group_by(Alert.alert_type).all()
    alert_type_stats = [{'type': t[0], 'count': t[1]} for t in alert_types]
    
    # 按设备统计未处理告警
    device_alerts = db.session.query(Alert.device_id, db.func.count(Alert.id)).\
        filter(Alert.is_handled == False).\
        group_by(Alert.device_id).all()
    
    device_stats = []
    for device_id, count in device_alerts:
        device = Device.query.get(device_id)
        if device:
            device_stats.append({
                'device_id': device_id,
                'device_name': device.name,
                'count': count
            })
    
    # 返回结果
    return jsonify({
        'daily_data': daily_data,
        'alert_type_stats': alert_type_stats,
        'device_stats': device_stats
    })


@alert.route('/handle/<int:id>', methods=['POST'])
@login_required
def handle(id):
    """处理告警"""
    alert = Alert.query.get_or_404(id)
    alert.is_handled = True
    alert.handled_by = g.user.id
    alert.handled_at = datetime.utcnow()
    db.session.commit()
    flash('告警已处理')
    return redirect(url_for('alert.index'))


@alert.route('/recover/<int:id>', methods=['POST'])
@login_required
def recover(id):
    """标记告警为已恢复"""
    alert = Alert.query.get_or_404(id)
    alert.is_recovered = True
    alert.recovered_at = datetime.utcnow()
    db.session.commit()
    flash('告警已标记为已恢复')
    return redirect(url_for('alert.view', id=id))


@alert.route('/view/<int:id>')
@login_required
def view(id):
    """查看告警详情"""
    alert = Alert.query.get_or_404(id)
    
    # 如果未读，则标记为已读
    if not alert.is_read:
        alert.is_read = True
        alert.read_at = datetime.utcnow()
        db.session.commit()
    
    return render_template('alert/view.html', title='告警详情', alert=alert)


@alert.route('/dashboard')
@login_required
def dashboard():
    """告警统计面板"""
    # 获取统计数据
    total = Alert.query.count()
    unhandled = Alert.query.filter_by(is_handled=False).count()
    critical = Alert.query.filter_by(severity='critical', is_handled=False).count()
    warning = Alert.query.filter_by(severity='warning', is_handled=False).count()
    info = Alert.query.filter_by(severity='info', is_handled=False).count()
    
    # 按设备统计未处理告警
    device_alerts = db.session.query(Alert.device_id, db.func.count(Alert.id)).\
        filter(Alert.is_handled == False).\
        group_by(Alert.device_id).all()
    
    device_stats = []
    for device_id, count in device_alerts:
        device = Device.query.get(device_id)
        if device:
            device_stats.append({
                'device_id': device_id,
                'device_name': device.name,
                'count': count
            })
    
    # 获取所有设备供查询表单使用
    devices = Device.query.all()
    
    return render_template('alert/dashboard.html', 
                          title='告警统计', 
                          total=total,
                          unhandled=unhandled,
                          critical=critical,
                          warning=warning,
                          info=info,
                          device_stats=device_stats,
                          devices=devices) 