from datetime import datetime
from app import db


class Traffic(db.Model):
    """流量数据模型"""
    __tablename__ = 'traffics'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'))
    interface = db.Column(db.String(64))  # 接口名称
    in_octets = db.Column(db.BigInteger)  # 入口流量（字节）
    out_octets = db.Column(db.BigInteger)  # 出口流量（字节）
    in_packets = db.Column(db.BigInteger)  # 入口数据包数
    out_packets = db.Column(db.BigInteger)  # 出口数据包数
    in_errors = db.Column(db.Integer)  # 入口错误数
    out_errors = db.Column(db.Integer)  # 出口错误数
    bandwidth = db.Column(db.BigInteger)  # 接口带宽（bps）
    utilization = db.Column(db.Float)  # 带宽利用率（百分比）
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Traffic {self.device_id}:{self.interface} at {self.timestamp}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'interface': self.interface,
            'in_octets': self.in_octets,
            'out_octets': self.out_octets,
            'in_packets': self.in_packets,
            'out_packets': self.out_packets,
            'in_errors': self.in_errors,
            'out_errors': self.out_errors,
            'bandwidth': self.bandwidth,
            'utilization': self.utilization,
            'timestamp': self.timestamp.isoformat()
        }


class TrafficStats(db.Model):
    """流量统计数据模型"""
    __tablename__ = 'traffic_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'))
    hour = db.Column(db.Integer)  # 小时（0-23）
    day = db.Column(db.Integer)  # 日期（1-31）
    month = db.Column(db.Integer)  # 月份（1-12）
    year = db.Column(db.Integer)  # 年份
    avg_in_rate = db.Column(db.Float)  # 平均入口速率（bps）
    avg_out_rate = db.Column(db.Float)  # 平均出口速率（bps）
    max_in_rate = db.Column(db.Float)  # 最大入口速率（bps）
    max_out_rate = db.Column(db.Float)  # 最大出口速率（bps）
    avg_utilization = db.Column(db.Float)  # 平均带宽利用率（百分比）
    peak_time = db.Column(db.DateTime)  # 流量峰值时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<TrafficStats {self.device_id} {self.year}-{self.month}-{self.day}>' 