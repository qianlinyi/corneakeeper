from flask_bootstrap import Bootstrap4
from flask_login import LoginManager, AnonymousUserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_moment import Moment
from flask_mail import Mail
from flask_ckeditor import CKEditor
from flask_wtf import CSRFProtect
from flask_dropzone import Dropzone
from flask_avatars import Avatars
from flask_whooshee import Whooshee

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


login_manager.anonymous_user = Guest
login_manager.login_view = 'auth.login'
# 需要添加其他方法获取 cookies
login_manager.login_message = u'请先登录您的账号 \\ Please log in to access page!'
login_manager.login_message_category = 'warning'
login_manager.refresh_view = 'auth.re_authenticate'
login_manager.needs_refresh_message_category = 'warning'
