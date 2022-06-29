from functools import wraps

from flask import Markup, flash, url_for, redirect, abort
from flask_login import current_user
from flask_babel import _


def confirm_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.confirmed:
            message = Markup(
                _(u'请先验证您的账户。没有收到邮件？') + '<a class="alert-link" href="{}">'.format(
                    url_for('auth.resend_confirm_email')) + _('重新发送验证邮件') + '</a>'
            )
            flash(message, 'warning')
            return redirect(url_for('blog.index'))
        return func(*args, **kwargs)

    return decorated_function


# 权限验证装饰器
def permission_required(permission_name):
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission_name):
                abort(403)
            return func(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(func):
    return permission_required('ADMINISTER')(func)
