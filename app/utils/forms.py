from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, IPAddress, ValidationError, Optional
from app.models.user import User
from app.models.device import Device
from app.models.terminal import Terminal


class LoginForm(FlaskForm):
    """登录表单"""
    username = StringField('用户名', validators=[DataRequired(message='用户名不能为空')])
    password = PasswordField('密码', validators=[DataRequired(message='密码不能为空')])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')


class RegistrationForm(FlaskForm):
    """注册表单"""
    username = StringField('用户名', validators=[DataRequired(message='用户名不能为空'), Length(min=3, max=64)])
    email = StringField('邮箱', validators=[DataRequired(message='邮箱不能为空'), Email(message='邮箱格式不正确')])
    name = StringField('姓名', validators=[Optional(), Length(max=64)])
    department = StringField('部门', validators=[Optional(), Length(max=64)])
    password = PasswordField('密码', validators=[DataRequired(message='密码不能为空'), Length(min=6, max=128)])
    password2 = PasswordField('确认密码', validators=[DataRequired(message='确认密码不能为空'), EqualTo('password', message='两次密码不一致')])
    submit = SubmitField('注册')
    
    def validate_username(self, username):
        """验证用户名是否已存在"""
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('该用户名已被使用')
    
    def validate_email(self, email):
        """验证邮箱是否已存在"""
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('该邮箱已被使用')


class DeviceForm(FlaskForm):
    """设备表单"""
    name = StringField('设备名称', validators=[DataRequired(message='设备名称不能为空'), Length(max=64)])
    ip_address = StringField('IP地址', validators=[DataRequired(message='IP地址不能为空'), IPAddress(message='IP地址格式不正确')])
    device_type = SelectField('设备类型', choices=[
        ('router', '路由器'),
        ('switch', '交换机'),
        ('firewall', '防火墙'),
        ('server', '服务器'),
        ('other', '其他')
    ])
    location = StringField('设备位置', validators=[Optional(), Length(max=128)])
    snmp_community = StringField('SNMP Community', validators=[Optional(), Length(max=64)], default='public')
    snmp_version = SelectField('SNMP版本', choices=[
        ('1', 'v1'),
        ('2c', 'v2c'),
        ('3', 'v3')
    ], default='2c')
    snmp_port = IntegerField('SNMP端口', validators=[Optional()], default=161)
    status = SelectField('设备状态', choices=[
        ('online', '在线'),
        ('offline', '离线'),
        ('maintenance', '维护中')
    ], default='online')
    description = TextAreaField('设备描述', validators=[Optional(), Length(max=500)])
    submit = SubmitField('提交')
    
    def validate_name(self, name):
        """验证设备名称是否已存在"""
        device = Device.query.filter_by(name=name.data).first()
        if device is not None and (not hasattr(self, 'id') or device.id != self.id.data):
            raise ValidationError('该设备名称已存在')
    
    def validate_ip_address(self, ip_address):
        """验证IP地址是否已存在"""
        device = Device.query.filter_by(ip_address=ip_address.data).first()
        if device is not None and (not hasattr(self, 'id') or device.id != self.id.data):
            raise ValidationError('该IP地址已被使用')


class TerminalForm(FlaskForm):
    """终端设备表单"""
    hostname = StringField('主机名', validators=[DataRequired(message='主机名不能为空'), Length(max=64)])
    ip_address = StringField('IP地址', validators=[DataRequired(message='IP地址不能为空'), IPAddress(message='IP地址格式不正确')])
    mac_address = StringField('MAC地址', validators=[DataRequired(message='MAC地址不能为空'), Length(max=17)])
    device_type = SelectField('设备类型', choices=[
        ('PC', '个人电脑'),
        ('Mobile', '手机'),
        ('Tablet', '平板电脑'),
        ('IoT', '物联网设备'),
        ('Server', '服务器'),
        ('Other', '其他')
    ])
    os_type = StringField('操作系统', validators=[Optional(), Length(max=32)])
    vendor = StringField('设备厂商', validators=[Optional(), Length(max=64)])
    location = StringField('物理位置', validators=[Optional(), Length(max=64)])
    connected_device_id = SelectField('连接的网络设备', validators=[Optional()], coerce=int)
    port_number = StringField('端口号', validators=[Optional(), Length(max=8)])
    vlan_id = StringField('VLAN ID', validators=[Optional(), Length(max=16)])
    connection_type = SelectField('连接类型', choices=[
        ('wired', '有线'),
        ('wireless', '无线')
    ], validators=[Optional()])
    is_active = BooleanField('是否活跃')
    user_agent = TextAreaField('用户代理', validators=[Optional()])
    submit = SubmitField('提交')
    
    def validate_hostname(self, hostname):
        """验证主机名是否已存在"""
        terminal = Terminal.query.filter_by(hostname=hostname.data).first()
        if terminal is not None and (not hasattr(self, 'id') or terminal.id != self.id.data):
            raise ValidationError('该主机名已存在')
    
    def validate_ip_address(self, ip_address):
        """验证IP地址是否已存在"""
        terminal = Terminal.query.filter_by(ip_address=ip_address.data).first()
        if terminal is not None and (not hasattr(self, 'id') or terminal.id != self.id.data):
            raise ValidationError('该IP地址已被使用')
    
    def validate_mac_address(self, mac_address):
        """验证MAC地址是否已存在"""
        terminal = Terminal.query.filter_by(mac_address=mac_address.data).first()
        if terminal is not None and (not hasattr(self, 'id') or terminal.id != self.id.data):
            raise ValidationError('该MAC地址已被使用')
    
    def __init__(self, *args, **kwargs):
        super(TerminalForm, self).__init__(*args, **kwargs)
        # 动态加载设备列表
        self.connected_device_id.choices = [(0, '-- 未连接 --')] + [
            (device.id, device.name) for device in Device.query.all()
        ]


class UserSettingsForm(FlaskForm):
    """用户设置表单"""
    name = StringField('姓名', validators=[DataRequired(), Length(max=64)])
    email = StringField('邮箱', validators=[DataRequired(), Email(), Length(max=120)])
    department = StringField('部门', validators=[Length(max=64)])
    current_password = PasswordField('当前密码')
    new_password = PasswordField('新密码', validators=[
        Optional(),
        Length(min=6, message='密码长度至少为6个字符'),
        EqualTo('confirm_password', message='两次输入的密码不一致')
    ])
    confirm_password = PasswordField('确认新密码')
    submit = SubmitField('保存修改') 