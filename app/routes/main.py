from flask import Blueprint, render_template, current_app
from datetime import datetime
from app.models.device import Device
from app.models.terminal import Terminal
from app.models.alert import Alert

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """系统主页"""
    # 获取基本统计数据
    device_count = Device.query.count()
    online_device_count = Device.query.filter_by(status='online').count()
    terminal_count = Terminal.query.count()
    alert_count = Alert.query.filter_by(status='open').count()
    
    # 获取最近未处理的告警
    recent_alerts = Alert.query.filter_by(status='open')\
                              .order_by(Alert.created_at.desc())\
                              .limit(5).all()
    
    return render_template('main/index.html', 
                          title='系统概览',
                          device_count=device_count,
                          online_device_count=online_device_count,
                          terminal_count=terminal_count,
                          alert_count=alert_count,
                          recent_alerts=recent_alerts)

@main.route('/about')
def about():
    """关于页面"""
    return render_template('main/../templates/heatmap/about.html',
                           title='关于系统',
                           now=datetime.now())