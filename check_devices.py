from app import create_app
from app.models.device import Device

app = create_app()
with app.app_context():
    devices = Device.query.all()
    print(f'设备总数: {len(devices)}')
    for device in devices:
        print(f'ID: {device.id}, 名称: {device.name}, 状态: {device.status}') 