from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from flask_babel import lazy_gettext as _l
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, HiddenField, \
    ValidationError, DateTimeField, FloatField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, Regexp, NumberRange

from corneakeeper.models import User


class EditProfileForm(FlaskForm):
    name = StringField(_l('昵称'), validators=[DataRequired(), Length(1, 30)])
    username = StringField(_l('用户名'), validators=[DataRequired(), Length(1, 20), Regexp('^[a-zA-Z0-9]*$',
                                                                                         message='The username should '
                                                                                                 'contain only a-z, '
                                                                                                 'A-Z and 0-9.')])
    website = StringField(_l('网站'), validators=[Optional(), Length(0, 255)])
    location = StringField(_l('地点'), validators=[Optional(), Length(0, 50)])
    bio = TextAreaField(_l('个性签名'), validators=[Optional(), Length(0, 120)])
    submit = SubmitField(_l('提交'))

    def validate_username(self, field):
        if field.data != current_user.username and User.query.filter_by(username=field.data).first():
            raise ValidationError(_l('用户名已被占用'))


class ChangeDataForm(FlaskForm):
    datetime = DateTimeField(_l('检测日期'), validators=[DataRequired()])
    updatetime = DateTimeField(_l('更新日期'), validators=[DataRequired()])
    k1 = FloatField('k1', validators=[DataRequired(), NumberRange(0, 100)])
    k2 = FloatField('k2', validators=[DataRequired(), NumberRange(0, 100)])
    k_max = FloatField(_l('最大曲率'), validators=[DataRequired(), NumberRange(0, 100)])
    thickness_min = IntegerField(_l('最薄点厚度'), validators=[DataRequired(), NumberRange(0, 700)])
    BSCVA = FloatField(_l('最佳眼镜矫正视力'), validators=[DataRequired(), NumberRange(0, 1.5)])
    UCVA = FloatField(_l('裸眼视力'), validators=[Optional(), NumberRange(0, 1.5)])
    submit = SubmitField(_l('提交'))


class UploadAvatarForm(FlaskForm):
    image = FileField(_l('上传'), validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png'], _l('文件后缀名为.jpg或者.png'))
    ])
    submit = SubmitField(_l('提交'))


class CropAvatarForm(FlaskForm):
    x = HiddenField()
    y = HiddenField()
    w = HiddenField()
    h = HiddenField()
    submit = SubmitField(_l('裁剪并保存'))


class ChangeEmailForm(FlaskForm):
    email = StringField(_l('新邮件'), validators=[DataRequired(), Length(1, 254), Email()])
    submit = SubmitField(_l('提交'))

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError(_l('邮箱已被占用'))


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField(_l('旧密码'), validators=[DataRequired()])
    password = PasswordField(_l('新密码'), validators=[
        DataRequired(), Length(8, 128), EqualTo('password2')])
    password2 = PasswordField(_l('验证密码'), validators=[DataRequired()])
    submit = SubmitField(_l('提交'))


class NotificationSettingForm(FlaskForm):
    receive_comment_notification = BooleanField(_l('新评论'))
    receive_follow_notification = BooleanField(_l('新粉丝'))
    receive_collect_notification = BooleanField(_l('新收藏'))
    submit = SubmitField(_l('提交'))


class PrivacySettingForm(FlaskForm):
    public_charts = BooleanField(_l('公开我的变化'))
    public_diagnosis = BooleanField(_l('公开我的诊断'))
    public_photos = BooleanField(_l('公开我的图片'))
    public_collections = BooleanField(_l('公开我的收藏'))
    public_followings = BooleanField(_l('公开我的关注'))
    public_followers = BooleanField(_l('公开我的粉丝'))
    submit = SubmitField(_l('提交'))


class DeleteAccountForm(FlaskForm):
    username = StringField(_l('用户名'), validators=[DataRequired(), Length(1, 20)])
    submit = SubmitField(_l('提交'))

    def validate_username(self, field):
        if field.data != current_user.username:
            raise ValidationError(_l('用户名错误'))
