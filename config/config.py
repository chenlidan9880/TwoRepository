import os
from dotenv import load_dotenv

# 加载环境变量
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """基本配置类"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 邮件服务器配置
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.163.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SENDER = os.environ.get('MAIL_SENDER', 'campus_network@example.com')
    
    # 阿里云短信服务配置
    ALIYUN_ACCESS_KEY_ID = os.environ.get('ALIYUN_ACCESS_KEY_ID')
    ALIYUN_ACCESS_KEY_SECRET = os.environ.get('ALIYUN_ACCESS_KEY_SECRET')
    ALIYUN_REGION_ID = os.environ.get('ALIYUN_REGION_ID', 'cn-hangzhou')
    ALIYUN_SMS_SIGN_NAME = os.environ.get('ALIYUN_SMS_SIGN_NAME', '校园网监控')
    ALIYUN_SMS_TEMPLATE_CODE = os.environ.get('ALIYUN_SMS_TEMPLATE_CODE', 'SMS_123456789')
    
    # SNMP配置
    SNMP_COMMUNITY = os.environ.get('SNMP_COMMUNITY', 'public')
    SNMP_VERSION = 2  # SNMP版本，1或2c
    SNMP_RETRIES = 3  # 重试次数
    SNMP_TIMEOUT = 1  # 超时时间（秒）
    
    # 流量监控配置
    TRAFFIC_MONITOR_INTERVAL = 60  # 数据采集间隔（秒）
    TRAFFIC_ALERT_THRESHOLD = 80  # 流量告警阈值（百分比）
    
    # 异常检测配置
    ANOMALY_DETECTION_INTERVAL = 300  # 异常检测间隔（秒）
    ANOMALY_DETECTION_WINDOW = 24 * 60 * 60  # 异常检测时间窗口（秒）
    
    @staticmethod
    def init_app(app):
        """初始化应用"""
        pass


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    # 使用MySQL数据库
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'mysql+pymysql://root:password@localhost/campus_network_dev'


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    # 使用MySQL数据库
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'mysql+pymysql://root:password@localhost/campus_network_test'


class ProductionConfig(Config):
    """生产环境配置"""
    # 使用MySQL数据库
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://root:password@localhost/campus_network_prod'


# 配置字典
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 