import os
from app import create_app, db, scheduler
from app.models.user import User
from app.models.device import Device
from app.models.traffic import Traffic
from app.models.alert import Alert
from app.models.terminal import Terminal
from init_sample_data import init_sample_data

# 设置环境变量启用调试模式
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '1'

# 创建应用
# app = create_app(os.getenv('FLASK_DEBUG', 'development'))
# 确保 config_name 是一个有效的配置名称
config_name = os.getenv('FLASK_CONFIG', 'development')
app = create_app(config_name)

def init_db():
    """初始化数据库"""
    print("创建数据库表...")
    db.create_all()
    print("数据库表创建完成!")

# 确保调度器仅启动一次
if not scheduler.running:
    scheduler.start()

if __name__ == '__main__':
    with app.app_context():
        # 检查数据库表是否存在
        try:
            User.query.first()
            print("数据库表已存在，跳过创建步骤")
        except Exception as e:
            print(f"数据库表不存在，开始创建: {e}")
            init_db()
            
        # 初始化示例数据
        try:
            init_sample_data()
        except Exception as e:
            print(f"初始化示例数据失败: {e}")

    # 启动Web应用
    print("启动Web应用...")
    app.run(host='0.0.0.0', port=5000, debug=True) 