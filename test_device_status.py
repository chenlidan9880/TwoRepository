from app import create_app, db
from app.models.device import Device

# 创建应用上下文
app = create_app()
with app.app_context():
    # 检查设备状态
    print('设备总数:', Device.query.count())
    
    # 检查所有可能的状态值
    status_values = db.session.query(Device.status).distinct().all()
    print('所有不同的状态值:', [status[0] for status in status_values])
    
    # 统计每种状态的设备数
    for status in status_values:
        status_value = status[0]
        count = Device.query.filter_by(status=status_value).count()
        print(f'状态为 "{status_value}" 的设备数量: {count}')
        
    # 特别检查"up"状态的设备
    up_devices = Device.query.filter_by(status='up').all()
    print(f'状态为 "up" 的设备数量: {len(up_devices)}')
    
    # 特别检查"online"状态的设备
    online_devices = Device.query.filter_by(status='online').all()
    print(f'状态为 "online" 的设备数量: {len(online_devices)}') 