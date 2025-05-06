from app import create_app, db
from app.models.device import Device

app = create_app()
with app.app_context():
    device = Device.query.filter_by(ip_address='192.168.176.1').first()
    print(f'Device: {device.id}, {device.name}, type: {device.device_type}, status: {device.status}')