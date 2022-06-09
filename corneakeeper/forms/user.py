from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, HiddenField, \
    ValidationError, DateTimeField, FloatField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, Regexp, NumberRange

from corneakeeper.models import User


class EditProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(1, 30)])
    username = StringField('Username', validators=[DataRequired(), Length(1, 20), Regexp('^[a-zA-Z0-9]*$',
                                                                                         message='The username should '
                                                                                                 'contain only a-z, '
                                                                                                 'A-Z and 0-9.')])
    website = StringField('Website', validators=[Optional(), Length(0, 255)])
    location = StringField('City', validators=[Optional(), Length(0, 50)])
    bio = TextAreaField('Bio', validators=[Optional(), Length(0, 120)])
    submit = SubmitField()

    def validate_username(self, field):
        if field.data != current_user.username and User.query.filter_by(username=field.data).first():
            raise ValidationError('The username is already in use.')


class ChangeDataForm(FlaskForm):
    datetime = DateTimeField('DateTime', validators=[DataRequired()])
    updatetime = DateTimeField('UpdateTime', validators=[DataRequired()])
    k1 = FloatField('k1', validators=[DataRequired(), NumberRange(0, 100)])
    k2 = FloatField('k2', validators=[DataRequired(), NumberRange(0, 100)])
    k_max = FloatField('k_max', validators=[DataRequired(), NumberRange(0, 100)])
    thickness_min = IntegerField('thickness_min', validators=[DataRequired(), NumberRange(0, 700)])
    BSCVA = FloatField('BSCVA', validators=[DataRequired(), NumberRange(0, 1.5)])
    UCVA = FloatField('UCVA', validators=[Optional(), NumberRange(0, 1.5)])
    submit = SubmitField()


class UploadAvatarForm(FlaskForm):
    image = FileField('Upload', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png'], 'The file format should be .jpg or .png.')
    ])
    submit = SubmitField()


class CropAvatarForm(FlaskForm):
    x = HiddenField()
    y = HiddenField()
    w = HiddenField()
    h = HiddenField()
    submit = SubmitField('Crop and Update')


class ChangeEmailForm(FlaskForm):
    email = StringField('New Email', validators=[DataRequired(), Length(1, 254), Email()])
    submit = SubmitField()

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('The email is already in use.')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old Password', validators=[DataRequired()])
    password = PasswordField('New Password', validators=[
        DataRequired(), Length(8, 128), EqualTo('password2')])
    password2 = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField()


class NotificationSettingForm(FlaskForm):
    receive_comment_notification = BooleanField('New comment')
    receive_follow_notification = BooleanField('New follower')
    receive_collect_notification = BooleanField('New collector')
    submit = SubmitField()


class PrivacySettingForm(FlaskForm):
    public_charts = BooleanField('Publc my charts')
    public_diagnosis = BooleanField('Public my diagnosis')
    public_photos = BooleanField('Public my photos')
    public_collections = BooleanField('Public my collection')
    public_followings = BooleanField('Public my followings')
    public_followers = BooleanField('Public my followers')
    submit = SubmitField()


class DeleteAccountForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 20)])
    submit = SubmitField()

    def validate_username(self, field):
        if field.data != current_user.username:
            raise ValidationError('Wrong username.')
