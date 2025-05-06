from flask import Blueprint, render_template
# 从app导入自定义login_required装饰器
from app import login_required, db
from app.models.device import Device
from app.models.alert import Alert
from app.models.terminal import Terminal

# 创建蓝图
main = Blueprint('main', __name__, url_prefix='/')

@main.route('/')
@main.route('/index')
@login_required
def index():
    """主页"""
    # 获取系统概览数据
    device_count = Device.query.count()
    online_device_count = Device.query.filter_by(status='online').count()
    alert_count = Alert.query.filter_by(is_handled=False).count()
    terminal_count = Terminal.query.count()
    
    # 获取最近5条告警
    recent_alerts = Alert.query.order_by(Alert.created_at.desc()).limit(5).all()
    
    return render_template('main/index.html', 
                          title='系统概览',
                          device_count=device_count,
                          online_device_count=online_device_count,
                          alert_count=alert_count,
                          terminal_count=terminal_count,
                          recent_alerts=recent_alerts)


@main.route('/about')
def about():
    """关于页面"""
    return render_template('main/../templates/heatmap/about.html', title='关于系统')