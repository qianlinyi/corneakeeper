from flask import request, current_app
from flask_bootstrap import Bootstrap4
from flask_login import LoginManager, AnonymousUserMixin, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_moment import Moment
from flask_mail import Mail
from flask_ckeditor import CKEditor
from flask_wtf import CSRFProtect
from flask_dropzone import Dropzone
from flask_avatars import Avatars
from flask_whooshee import Whooshee
from flask_babel import Babel, lazy_gettext as _l

login_manager = LoginManager()
db = SQLAlchemy()
bootstrap = Bootstrap4()
moment = Moment()
mail = Mail()
ckeditor = CKEditor()
csrf = CSRFProtect()
dropzone = Dropzone()
avatars = Avatars()
whooshee = Whooshee()
babel = Babel()


#  用户加载函数
@login_manager.user_loader
def load_user(user_id):
    from corneakeeper.models import User
    user = User.query.get(int(user_id))
    return user


class Guest(AnonymousUserMixin):
    @property
    def is_admin(self):
        return False

    def can(self, permission_name):
        return False


@babel.localeselector
def get_locale():
    if current_user.is_authenticated and current_user.locale is not None:
        return current_user.locale

    locale = request.cookies.get('locale')
    if locale is not None:
        return locale
    return request.accept_languages.best_match(current_app.config['CK_LOCALES'])


login_manager.anonymous_user = Guest
login_manager.login_view = 'auth.login'
login_manager.login_message = _l(u'请先登录您的账号')
login_manager.login_message_category = 'warning'
login_manager.refresh_view = 'auth.re_authenticate'
login_manager.needs_refresh_message_category = 'warning'
