from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from app import db, login_required
from app.models.user import User
from wtforms import Form, StringField, BooleanField, PasswordField, validators

# 创建蓝图
user = Blueprint('user', __name__, url_prefix='/user')

# 表单类
class ProfileForm(Form):
    """用户个人资料表单"""
    username = StringField('用户名', [validators.Length(min=3, max=25)])
    name = StringField('姓名', [validators.Length(min=2, max=50)])
    email = StringField('电子邮箱', [validators.Email()])
    phone_number = StringField('手机号码', [validators.Optional(), validators.Regexp(r'^\d{11}$', message='请输入正确的11位手机号码')])
    department = StringField('部门', [validators.Optional(), validators.Length(max=50)])
    receive_email = BooleanField('接收邮件通知')
    receive_sms = BooleanField('接收短信通知')
    critical_only = BooleanField('仅接收紧急告警')
    password = PasswordField('新密码', [validators.Optional(), validators.Length(min=6)])
    confirm = PasswordField('确认密码', [
        validators.Optional(),
        validators.EqualTo('password', message='密码不匹配')
    ])

@user.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """用户个人资料页面"""
    user = g.user
    form = ProfileForm(request.form)
    
    # 处理表单提交
    if request.method == 'POST' and form.validate():
        # 更新基本信息
        user.name = form.name.data
        user.email = form.email.data
        user.phone_number = form.phone_number.data
        user.department = form.department.data
        
        # 更新通知设置
        preferences = user.notification_preferences or {}
        preferences.update({
            'email': form.receive_email.data,
            'sms': form.receive_sms.data,
            'critical_only': form.critical_only.data
        })
        user.notification_preferences = preferences
        
        # 更新密码（如果提供）
        if form.password.data:
            user.set_password(form.password.data)
        
        # 保存更改
        db.session.commit()
        flash('个人资料已成功更新')
        return redirect(url_for('user.profile'))
    
    # GET请求: 填充表单
    if request.method == 'GET':
        form.username.data = user.username
        form.name.data = user.name
        form.email.data = user.email
        form.phone_number.data = user.phone_number
        form.department.data = user.department
        
        # 设置通知偏好
        preferences = user.notification_preferences or {}
        form.receive_email.data = preferences.get('email', True)
        form.receive_sms.data = preferences.get('sms', False)
        form.critical_only.data = preferences.get('critical_only', False)
    
    return render_template('user/profile.html', title='个人资料', form=form) 