from flask import render_template, flash, redirect, url_for, Blueprint, request
from flask_login import login_user, logout_user, login_required, current_user, login_fresh, confirm_login
from flask_babel import _
from corneakeeper.utils import redirect_back, generate_token, validate_token, Operations
from corneakeeper.extensions import db
from corneakeeper.forms.auth import LoginForm, RegisterForm, ForgetPasswordForm, ResetPasswordForm
from corneakeeper.models import User
from corneakeeper.emails import send_confirm_email
from corneakeeper.emails import send_reset_password_email

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/test')
def test():
    return render_template('auth/test.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('blog.index'))
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember = form.remember.data
        user = User.query.filter_by(username=username).first()
        if user:
            if username == user.username and user.validate_password(password):
                login_user(user, remember)
                flash(_('欢迎回来'), 'info')
                return redirect_back()
            else:
                flash(_('无效用户名或密码'), 'warning')
        else:
            flash(_('账户不存在'), 'warning')
    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash(_('登出成功'), 'info')
    return redirect(url_for('blog.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('blog.index'))
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data.lower()
        username = form.username.data
        password = form.password.data
        user = User(name=name, email=email, username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        token = generate_token(user=user, operation='confirm')
        send_confirm_email(template='emails/confirm', user=user, token=token)
        flash(_('验证邮件已发送，请检查您的邮箱'), 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@auth_bp.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('blog.index'))
    if validate_token(user=current_user, token=token, operation=Operations.CONFIRM):
        flash(_('用户验证成功'), 'success')
        return redirect(url_for('blog.index'))
    else:
        flash(_('token 无效或已过期'), 'danger')
        return redirect(url_for('.resend_confirm_email'))


@auth_bp.route('/resend-confirm-email')
@login_required
def resend_confirm_email():
    if current_user.confirmed:
        return redirect(url_for('blog.index'))
    token = generate_token(user=current_user, operation=Operations.CONFIRM)
    send_confirm_email(template='emails/confirm', user=current_user, token=token)
    flash(_('新邮件已发出，检查您的邮箱'), 'info')
    return redirect(url_for('blog.index'))


@auth_bp.route('/forget-password', methods=['GET', 'POST'])
def forget_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ForgetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = generate_token(user=user, operation=Operations.RESET_PASSWORD)
            send_reset_password_email(user=user, token=token)
            flash(_('密码重置邮件已发送，请查看您的邮箱'), 'info')
            return redirect(url_for('.login'))
        flash(_('无效的邮箱地址'), 'warning')
        return redirect(url_for('.forget_password'))
    return render_template('auth/reset_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('blog.index'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user is None:
            return redirect(url_for('blog.index'))
        if validate_token(user=user, token=token, operation=Operations.RESET_PASSWORD,
                          new_password=form.password.data):
            flash(_('密码重置成功'), 'success')
            return redirect(url_for('.login'))
        else:
            flash(_('链接无效或已过期'), 'danger')
            return redirect(url_for('.forget_password'))
    return render_template('auth/reset_password.html', form=form)


@auth_bp.route('/re-authenticate', methods=['GET', 'POST'])
@login_required
def re_authenticate():
    if login_fresh():
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit() and current_user.validate_password(form.password.data):
        confirm_login()
        return redirect_back()
    return render_template('auth/login.html', form=form)
