"""
校园网终端设备监控系统启动脚本
"""
import os
from app import create_app, db, scheduler
from flask_migrate import Migrate

# 导入模型以确保数据库表被创建
from app.models.user import User
from app.models.device import Device
from app.models.terminal import Terminal
from app.models.traffic import Traffic, TrafficStats
from app.models.alert import Alert
from app.models.settings import Settings

# 初始化OUI数据库
from app.utils.terminal_identifier import init_oui_database

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Device=Device, Terminal=Terminal,
                Traffic=Traffic, TrafficStats=TrafficStats, Alert=Alert)

@app.cli.command()
def deploy():
    """部署命令"""
    # 创建数据库表
    db.create_all()

    # 检查是否有管理员用户，如果没有则创建
    admin = User.query.filter_by(username='admin').first()
    if admin is None:
        admin = User(username='admin',
                     email='admin@example.com',
                     role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

    # 初始化终端设备OUI数据库
    with app.app_context():
        init_oui_database()

    # 启动调度器
    if not scheduler.running:
        scheduler.start()
        
        # 添加调度任务
        from app.utils.scheduler import poll_devices, discover_terminals
        
        # 添加每5分钟执行一次的设备数据采集任务
        if not scheduler.get_job('poll_devices_job'):
            scheduler.add_job(
                func=poll_devices,
                trigger='interval',
                minutes=5,
                id='poll_devices_job',
                replace_existing=True,
                name='设备流量数据采集'
            )
        
        # 添加每15分钟执行一次的终端设备发现任务
        if not scheduler.get_job('discover_terminals_job'):
            scheduler.add_job(
                func=discover_terminals,
                trigger='interval',
                minutes=15,
                id='discover_terminals_job',
                replace_existing=True,
                name='终端设备发现'
            )

    print('部署完成!')

@app.cli.command()
def init_db():
    """初始化数据库"""
    db.create_all()

    # 检查是否有管理员用户，如果没有则创建
    admin = User.query.filter_by(username='admin').first()
    if admin is None:
        admin = User(username='admin',
                     email='admin@example.com',
                     role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

    # 初始化终端设备OUI数据库
    with app.app_context():
        init_oui_database()

    # 启动调度器
    if not scheduler.running:
        scheduler.start()

    print('数据库初始化完成!')

@app.cli.command()
def create_migration():
    """创建数据库迁移脚本"""
    os.system('flask db init')
    os.system('flask db migrate -m "initial migration"')
    print('数据库迁移脚本创建完成!')

@app.before_first_request
def before_first_request():
    """应用首次请求前的初始化操作"""
    # 确保数据库表存在
    db.create_all()

    # 初始化终端设备OUI数据库
    init_oui_database()

    # 启动调度器
    if not scheduler.running:
        scheduler.start()
        
        # 添加调度任务
        from app.utils.scheduler import poll_devices, discover_terminals
        
        # 添加每5分钟执行一次的设备数据采集任务
        if not scheduler.get_job('poll_devices_job'):
            scheduler.add_job(
                func=poll_devices,
                trigger='interval',
                minutes=5,
                id='poll_devices_job',
                replace_existing=True,
                name='设备流量数据采集'
            )
        
        # 添加每15分钟执行一次的终端设备发现任务
        if not scheduler.get_job('discover_terminals_job'):
            scheduler.add_job(
                func=discover_terminals,
                trigger='interval',
                minutes=15,
                id='discover_terminals_job',
                replace_existing=True,
                name='终端设备发现'
            )

    app.logger.info("应用初始化完成")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 