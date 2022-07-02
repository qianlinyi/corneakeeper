from flask_wtf import FlaskForm
from flask_ckeditor import CKEditorField
from flask_babel import lazy_gettext as _l
from wtforms import StringField, SubmitField, TextAreaField, HiddenField, SelectField
from wtforms.validators import DataRequired, Length, Email, Optional, URL, ValidationError
from corneakeeper.models import Category


class CommentForm(FlaskForm):
    author = StringField(_l('姓名'), validators=[DataRequired(), Length(1, 30)])
    email = StringField(_l('邮箱'), validators=[DataRequired(), Email(), Length(1, 254)])
    site = StringField(_l('网址'), validators=[Optional(), URL(), Length(0, 255)])
    body = TextAreaField(_l('评论'), validators=[DataRequired()])
    submit = SubmitField(_l('提交'))


class UserCommentForm(CommentForm):
    author = HiddenField()
    email = HiddenField()
    site = HiddenField()


class PostForm(FlaskForm):
    title = StringField(_l('标题'), validators=[DataRequired(), Length(1, 60)])
    category = SelectField(_l('分类'), coerce=int, default=1)
    body = CKEditorField(_l('内容'), validators=[DataRequired()])
    submit = SubmitField(_l('提交'))

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.category.choices = [(category.id, category.name)
                                 for category in Category.query.order_by(Category.name).all()]


class CategoryForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(1, 30)])
    submit = SubmitField()

    def validate_name(self, field):
        if Category.query.filter_by(name=field.data).first():
            raise ValidationError('Name already in use.')


class LinkForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(1, 30)])
    url = StringField('URL', validators=[DataRequired(), URL(), Length(1, 255)])
    submit = SubmitField()
