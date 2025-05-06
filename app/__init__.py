"""
应用初始化模块，创建和配置Flask应用
"""

import os
from datetime import datetime  # 添加datetime导入
from flask import Flask, session, g, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
# from flask_login import LoginManager  # 注释掉Flask-Login
from flask_migrate import Migrate
from flask_caching import Cache
from flask_apscheduler import APScheduler
import functools

# 创建SQLAlchemy实例
db = SQLAlchemy()

# 创建缓存实例
cache = Cache()

# 不再使用LoginManager
# login_manager = LoginManager()

# 创建调度器实例
scheduler = APScheduler()

# 自定义登录所需功能
def login_required(view):
    """用于保护需要登录的视图的装饰器"""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login', next=request.url))
        return view(**kwargs)
    return wrapped_view

def create_app(test_config=None):
    """创建并配置Flask应用"""
    # 创建Flask应用
    app = Flask(__name__, instance_relative_config=True)
    
    # 配置日志
    import logging
    from logging.handlers import RotatingFileHandler
    import os
    
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/campus_network.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('校园网监控系统启动')
    
    # 设置默认配置
    app.config.from_mapping(
        SECRET_KEY='dev',
        SQLALCHEMY_DATABASE_URI=os.environ.get('DEV_DATABASE_URL', 'sqlite:///campus_network.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        CACHE_TYPE='SimpleCache',
        CACHE_DEFAULT_TIMEOUT=300,
        CACHE_MAX_TRAFFIC_POINTS=100,
        CACHE_TRAFFIC_TIMEOUT=3600,
        CACHE_MAX_STATS_POINTS=50,
        CACHE_STATS_TIMEOUT=3600,
        DATA_RETENTION_DAYS=90,
        DATA_ARCHIVE_DAYS=30
    )
    
    # 设置开发环境
    app.config['ENV'] = os.environ.get('FLASK_ENV', 'development')
    app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', '0') == '1'
    
    # 确保加载正确的配置文件
    if test_config is None:
        # 从config.py加载配置
        from config.config import DevelopmentConfig, TestingConfig, ProductionConfig
        
        config_name = os.environ.get('FLASK_CONFIG', 'development')
        if config_name == 'development':
            app.config.from_object(DevelopmentConfig)
        elif config_name == 'testing':
            app.config.from_object(TestingConfig)
        elif config_name == 'production':
            app.config.from_object(ProductionConfig)
            
        app.logger.info(f'数据库连接: {app.config["SQLALCHEMY_DATABASE_URI"]}')
    else:
        # 加载测试配置
        if isinstance(test_config, str):
            # 如果是字符串，认为是配置名称
            from config.config import DevelopmentConfig, TestingConfig, ProductionConfig
            if test_config == 'development':
                app.config.from_object(DevelopmentConfig)
            elif test_config == 'testing':
                app.config.from_object(TestingConfig)
            elif test_config == 'production':
                app.config.from_object(ProductionConfig)
            app.logger.info(f'从字符串加载配置: {test_config}')
        else:
            # 如果是字典，直接使用
            app.config.from_mapping(test_config)
    
    # 确保实例文件夹存在
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # 初始化数据库
    db.init_app(app)
    
    # 初始化缓存
    cache.init_app(app)
    
    # 不再初始化LoginManager
    # login_manager.init_app(app)
    # login_manager.login_view = 'auth.login'
    # login_manager.login_message = '请先登录'
    
    # 添加自定义用户加载逻辑
    @app.before_request
    def load_logged_in_user():
        user_id = session.get('user_id')
        
        if user_id is None:
            g.user = None
        else:
            from app.models.user import User
            g.user = User.query.get(int(user_id))
    
    # 添加current_user代理，供模板使用
    @app.context_processor
    def utility_processor():
        return {'current_user': g.user}
    
    # 添加now变量供模板使用
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}
    
    # 初始化数据库迁移
    migrate = Migrate(app, db)
    
    # 初始化调度器
    scheduler.init_app(app)
    # 仅当应用不是通过flask run命令启动时才启动调度器
    if not os.environ.get('FLASK_RUN_FROM_CLI'):
        # 注册流量处理任务
        @scheduler.task('interval', id='traffic_stats_processor', hours=1, misfire_grace_time=900)
        def traffic_stats_job():
            """每小时运行一次的流量统计处理任务"""
            with app.app_context():
                from app.utils.traffic_processor import process_traffic_stats
                app.logger.info("开始运行hourly流量统计处理...")
                result = process_traffic_stats()
                app.logger.info(f"流量统计处理结果: {result}")

        @scheduler.task('cron', id='daily_traffic_stats', hour=0, minute=5, misfire_grace_time=3600)
        def daily_traffic_stats_job():
            """每天凌晨12:05运行一次的每日流量统计处理任务"""
            with app.app_context():
                from app.utils.traffic_processor import process_daily_stats
                app.logger.info("开始运行daily流量统计处理...")
                result = process_daily_stats()
                app.logger.info(f"每日流量统计处理结果: {result}")
            
        scheduler.start()
    
    # 注册蓝图
    from app.controllers.auth import auth as auth_blueprint
    from app.controllers.main import main as main_blueprint
    from app.controllers.device import device as device_blueprint
    from app.controllers.monitor import monitor as monitor_blueprint
    from app.controllers.alert import alert as alert_blueprint
    from app.controllers.terminal import terminal as terminal_blueprint
    from app.controllers.heatmap import heatmap as heatmap_blueprint
    from app.routes.topology import topology_bp as topology_blueprint
    from app.routes.dashboard import dashboard_bp as dashboard_blueprint
    
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(main_blueprint)
    app.register_blueprint(device_blueprint)
    app.register_blueprint(monitor_blueprint)
    app.register_blueprint(alert_blueprint)
    app.register_blueprint(terminal_blueprint)
    app.register_blueprint(heatmap_blueprint)
    app.register_blueprint(topology_blueprint)
    app.register_blueprint(dashboard_blueprint)
    
    # 添加错误处理程序
    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error(f"500 错误: {str(e)}")
        return "服务器内部错误，请查看日志获取详细信息", 500
    
    @app.errorhandler(404)
    def page_not_found(e):
        return "页面未找到", 404
    
    # 在应用启动之前初始化数据库和其他组件
    with app.app_context():
        # 初始化数据库表
        db.create_all()
        
        # 不再使用login_manager
        # 导入User模型
        from app.models.user import User
        
        # 添加应用启动时的其他初始化
        @app.before_first_request
        def before_first_request():
            """应用启动时执行的初始化操作"""
            # 直接导入需要的函数，避免循环导入
            from app.utils.terminal_identifier import init_oui_database
            from app.utils.data_storage import init_storage
            from app.utils.data_processor import init_processor_pipeline
            from app.utils.flow_collector import init_flow_collectors
            
            # 初始化OUI数据库
            init_oui_database()
            
            # 初始化数据存储层
            init_storage()
            
            # 初始化数据处理流水线
            init_processor_pipeline()
            
            # 初始化流量收集器
            init_flow_collectors()
            
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
    
    return app

# 移除全局应用实例
# app = create_app()

# 导入模型，确保在创建表之前定义了所有模型
from app.models import user, device, terminal, traffic, alert 