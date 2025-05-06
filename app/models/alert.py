from datetime import datetime
from app import db


class Alert(db.Model):
    """告警模型"""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'))
    alert_type = db.Column(db.String(32))  # 告警类型：traffic_high, traffic_anomaly, device_down
    severity = db.Column(db.String(16))  # 严重程度：info, warning, critical
    title = db.Column(db.String(128))  # 告警标题
    message = db.Column(db.Text)  # 告警详情
    value = db.Column(db.Float)  # 告警触发值
    threshold = db.Column(db.Float)  # 告警阈值
    is_read = db.Column(db.Boolean, default=False)  # 是否已读
    read_at = db.Column(db.DateTime)  # 读取时间
    is_handled = db.Column(db.Boolean, default=False)  # 是否已处理
    handled_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # 处理人
    handled_at = db.Column(db.DateTime)  # 处理时间
    is_recovered = db.Column(db.Boolean, default=False)  # 是否已恢复
    recovered_at = db.Column(db.DateTime)  # 恢复时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 建立与Device模型的关联
    device = db.relationship('Device', backref='alerts')
    
    def __repr__(self):
        return f'<Alert {self.id} {self.alert_type} {self.severity}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'device_name': self.device.name if self.device else None,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'title': self.title,
            'message': self.message,
            'value': self.value,
            'threshold': self.threshold,
            'is_read': self.is_read,
            'is_handled': self.is_handled,
            'created_at': self.created_at.isoformat()
        }
    
    @staticmethod
    def from_dict(data):
        """从字典创建告警"""
        alert = Alert()
        for field in ['device_id', 'alert_type', 'severity', 'title', 
                      'message', 'value', 'threshold']:
            if field in data:
                setattr(alert, field, data[field])
        return alert 