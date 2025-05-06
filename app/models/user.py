from werkzeug.security import generate_password_hash, check_password_hash
# 不再继承UserMixin
# from flask_login import UserMixin
from datetime import datetime
from app import db  # 不再导入login_manager


class User(db.Model):  # 不再继承UserMixin
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(64))
    department = db.Column(db.String(64))
    phone_number = db.Column(db.String(20))  # 新增手机号字段
    notification_preferences = db.Column(db.JSON, default={
        "email": True,
        "sms": False,
        "critical_only": False
    })  # 通知偏好设置
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 用于替代UserMixin的功能
    @property
    def is_authenticated(self):
        return True
        
    @property
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)
    
    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """检查密码"""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """更新最后登录时间"""
        self.last_login = datetime.utcnow()
    
    def __repr__(self):
        return f'<User {self.username}>'


# 不再需要user_loader
# @login_manager.user_loader
# def load_user(user_id):
#     """加载用户"""
#     return User.query.get(int(user_id)) 