from app import create_app, db
from app.models.terminal import Terminal
from app.models.device import Device

# 创建应用上下文
app = create_app()
with app.app_context():
    # 检查设备和终端数据
    print('设备总数:', Device.query.count())
    
    # 查看每个设备的终端数量
    for device in Device.query.all():
        terminals_count = Terminal.query.filter_by(connected_device_id=device.id).count()
        print(f'设备ID: {device.id}, 名称: {device.name}, 终端数量: {terminals_count}')
        
        # 列出该设备连接的终端详情
        if terminals_count > 0:
            print(f'  连接的终端设备:')
            for terminal in Terminal.query.filter_by(connected_device_id=device.id).all():
                print(f'    - 终端ID: {terminal.id}, 主机名: {terminal.hostname}, IP: {terminal.ip_address}') 