from flask_wtf import FlaskForm
from flask_babel import lazy_gettext as _l
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms import ValidationError
from wtforms.validators import DataRequired, Length, Email, EqualTo, Regexp
from werkzeug.security import check_password_hash
from corneakeeper.models import User


class LoginForm(FlaskForm):
    username = StringField(_l('用户名'), validators=[DataRequired(), Length(0, 20)])
    password = PasswordField(_l('密码'), validators=[DataRequired(), Length(1, 128)])
    remember = BooleanField(_l('记住我'))
    submit = SubmitField(_l('提交'))


class RegisterForm(FlaskForm):
    name = StringField(_l('昵称'), validators=[DataRequired(), Length(1, 30)])
    email = StringField(_l('邮箱'), validators=[DataRequired(), Length(1, 254), Email()])
    username = StringField(_l('用户名'), validators=[DataRequired(), Length(1, 20), Regexp('^[a-zA-Z0-9]*$',
                                                                                        message='The username should '
                                                                                                'contain only a-z, '
                                                                                                'A-Z and 0-9.')])
    password = PasswordField(_l('密码'), validators=[
        DataRequired(), Length(8, 128), EqualTo('password2')])
    password2 = PasswordField(_l('确认密码'), validators=[DataRequired()])
    submit = SubmitField(_l('提交'))

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('The email is already in use.')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('The username is already in use.')


class ForgetPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 254), Email()])
    submit = SubmitField()


class ResetPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 254), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(), Length(8, 128), EqualTo('password2')])
    password2 = PasswordField('Confirm password', validators=[DataRequired()])
    submit = SubmitField()

    def validate_password(self, field):
        user = User.query.filter_by(email=self.email.data).first()
        if check_password_hash(user.password_hash, field.data):
            raise ValidationError('The password is the same as before.')
