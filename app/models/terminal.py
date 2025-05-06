from datetime import datetime
from app import db


class Terminal(db.Model):
    """终端设备模型"""
    __tablename__ = 'terminals'
    
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(64), nullable=False)
    ip_address = db.Column(db.String(15), unique=True, nullable=False)
    mac_address = db.Column(db.String(17), unique=True, nullable=False)
    device_type = db.Column(db.String(32))  # 设备类型：个人电脑、手机、平板等
    os_type = db.Column(db.String(32))      # 操作系统类型
    vendor = db.Column(db.String(64))       # 设备厂商
    user_agent = db.Column(db.Text)         # 用户代理字符串
    is_active = db.Column(db.Boolean, default=False)  # 是否活跃
    location = db.Column(db.String(64))     # 物理位置
    
    # 与网络设备的关联（单向多对一关系）
    connected_device_id = db.Column(db.Integer, db.ForeignKey('devices.id'))
    connected_device = db.relationship('Device', 
                                     backref=db.backref('connected_terminals', lazy='dynamic'),
                                     foreign_keys=[connected_device_id])
    
    # 添加连接信息
    port_number = db.Column(db.String(8))    # 连接的端口号
    vlan_id = db.Column(db.String(16))       # VLAN ID
    connection_type = db.Column(db.String(16))  # 连接类型：有线/无线
    
    # 流量统计
    in_traffic = db.Column(db.BigInteger, default=0)  # 入站流量（字节）
    out_traffic = db.Column(db.BigInteger, default=0)  # 出站流量（字节）
    bandwidth_usage = db.Column(db.Float, default=0)  # 带宽使用率
    
    # 时间戳
    first_seen = db.Column(db.DateTime, default=datetime.now)
    last_seen = db.Column(db.DateTime, default=datetime.now)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<Terminal {self.hostname}>'
    
    def to_dict(self):
        """转换为字典"""
        # 获取活跃状态对应的status字符串
        status = 'online' if self.is_active else 'offline'
        
        return {
            'id': self.id,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'mac_address': self.mac_address,
            'device_type': self.device_type,
            'os_type': self.os_type,
            'vendor': self.vendor,
            'status': status,
            'is_active': self.is_active,
            'location': self.location,
            'connected_device': self.connected_device.name if self.connected_device else None,
            'connected_device_id': self.connected_device_id,
            'port_number': self.port_number,
            'vlan_id': self.vlan_id,
            'connection_type': self.connection_type,
            'in_traffic': self.in_traffic,
            'out_traffic': self.out_traffic,
            'bandwidth_usage': self.bandwidth_usage,
            'first_seen': self.first_seen.strftime('%Y-%m-%d %H:%M:%S') if self.first_seen else None,
            'last_seen': self.last_seen.strftime('%Y-%m-%d %H:%M:%S') if self.last_seen else None,
            'user_agent': self.user_agent
        }
    
    @staticmethod
    def from_dict(data):
        """从字典创建终端设备"""
        terminal = Terminal()
        for field in ['hostname', 'ip_address', 'mac_address', 'device_type', 
                     'os_type', 'vendor', 'user_agent', 'location', 'connected_device_id', 
                     'port_number', 'vlan_id', 'connection_type', 'in_traffic', 'out_traffic', 'bandwidth_usage']:
            if field in data:
                setattr(terminal, field, data[field])
        
        # 特殊处理status字段
        if 'status' in data:
            terminal.is_active = (data['status'] == 'online')
        # 直接处理is_active字段
        elif 'is_active' in data:
            terminal.is_active = data['is_active']
        
        return terminal 