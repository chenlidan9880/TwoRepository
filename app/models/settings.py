"""
系统设置模型
用于存储系统配置项
"""

from app import db
from datetime import datetime

class Settings(db.Model):
    """系统设置模型类"""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False, default='string')  # string, integer, float, boolean
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, nullable=False)
    
    @staticmethod
    def get_value(key, default=None):
        """
        获取设置值
        
        参数:
            key: 设置键名
            default: 默认值，如果设置不存在则返回此值
        
        返回:
            设置值，根据type转换为相应的类型
        """
        setting = Settings.query.filter_by(key=key).first()
        
        if not setting:
            return default
        
        # 根据类型转换值
        if setting.type == 'integer':
            return int(setting.value)
        elif setting.type == 'float':
            return float(setting.value)
        elif setting.type == 'boolean':
            return setting.value.lower() in ('true', 'yes', '1')
        else:
            return setting.value
    
    @staticmethod
    def set_value(key, value, type='string', description=None):
        """
        设置值
        
        参数:
            key: 设置键名
            value: 设置值
            type: 值类型，可选string, integer, float, boolean
            description: 设置描述
        
        返回:
            设置对象
        """
        setting = Settings.query.filter_by(key=key).first()
        
        if setting:
            setting.value = str(value)
            setting.updated_at = datetime.now()
            if type:
                setting.type = type
            if description:
                setting.description = description
        else:
            setting = Settings(
                key=key,
                value=str(value),
                type=type,
                description=description,
                updated_at=datetime.now()
            )
            db.session.add(setting)
        
        db.session.commit()
        return setting
    
    def __repr__(self):
        return f'<Settings {self.key}={self.value}>' 