from flask import Blueprint, render_template, redirect, url_for, flash, request, session, g
from werkzeug.urls import url_parse
from app import db, login_required
from app.models.user import User
from app.utils.forms import LoginForm, RegistrationForm
from datetime import datetime

# 创建蓝图
auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    # 如果用户已经登录，重定向到首页
    if g.user is not None:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('用户名或密码错误')
            return redirect(url_for('auth.login'))
        
        # 将用户ID存储在session中
        session.clear()
        session['user_id'] = user.id
        session['remember'] = form.remember_me.data
        
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        return redirect(next_page)
    
    return render_template('auth/login.html', title='登录', form=form)


@auth.route('/logout')
@login_required
def logout():
    """用户退出"""
    session.clear()
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    # 如果用户已经登录，重定向到首页
    if g.user is not None:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            name=form.name.data,
            department=form.department.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('注册成功，请登录')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='注册', form=form)


@auth.route('/profile')
@login_required
def profile():
    """用户个人中心"""
    return render_template('auth/profile.html', title='个人中心')


@auth.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """账户设置页面"""
    from app.utils.forms import UserSettingsForm
    
    form = UserSettingsForm(obj=g.user)
    
    if form.validate_on_submit():
        # 更新用户基本信息
        g.user.name = form.name.data
        g.user.email = form.email.data
        g.user.department = form.department.data
        
        # 如果提供了新密码
        if form.new_password.data:
            if not g.user.check_password(form.current_password.data):
                flash('当前密码不正确', 'danger')
                return render_template('auth/settings.html', title='账户设置', form=form)
            
            g.user.set_password(form.new_password.data)
        
        db.session.commit()
        flash('账户信息已更新', 'success')
        return redirect(url_for('auth.settings'))
    
    return render_template('auth/settings.html', title='账户设置', form=form) 