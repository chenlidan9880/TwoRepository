from datetime import datetime
from app import db


class Device(db.Model):
    """网络设备模型"""
    __tablename__ = 'devices'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, index=True)
    ip_address = db.Column(db.String(15), unique=True, index=True)
    device_type = db.Column(db.String(32))  # 路由器、交换机等
    location = db.Column(db.String(128))  # 设备位置
    snmp_community = db.Column(db.String(64), default='public')
    snmp_version = db.Column(db.String(8), default='2c')
    snmp_port = db.Column(db.Integer, default=161)
    status = db.Column(db.String(16), default='online')  # online, offline, maintenance
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 与Traffic模型关联
    traffics = db.relationship('Traffic', backref='device', lazy='dynamic')
    
    # 移除冲突的与Terminal模型关联，由Terminal模型维护关系
    # terminals = db.relationship('Terminal', backref='connected_device', lazy='dynamic')
    
    def __repr__(self):
        return f'<Device {self.name}>'
    
    def to_dict(self):
        """转换为字典"""
        # 计算关联的终端数量
        from app.models.terminal import Terminal
        connected_terminals_count = Terminal.query.filter_by(connected_device_id=self.id).count()
        
        return {
            'id': self.id,
            'name': self.name,
            'ip_address': self.ip_address,
            'device_type': self.device_type,
            'location': self.location,
            'status': self.status,
            'description': self.description,
            'connected_terminals_count': connected_terminals_count
        }
    
    @staticmethod
    def from_dict(data):
        """从字典创建设备"""
        device = Device()
        for field in ['name', 'ip_address', 'device_type', 'location',
                     'snmp_community', 'snmp_version', 'snmp_port',
                     'status', 'description']:
            if field in data:
                setattr(device, field, data[field])
        return device 