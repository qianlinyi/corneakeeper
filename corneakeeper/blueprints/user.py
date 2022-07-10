import os
from sqlalchemy import and_
from flask import render_template, redirect, url_for, flash, request, \
    current_app, Blueprint, abort
from flask_login import current_user, fresh_login_required, login_required, \
    logout_user
from flask_babel import _
from pyecharts import options as opts
from pyecharts.globals import ThemeType
from pyecharts.charts import Line
from corneakeeper.decorators import confirm_required, permission_required
from corneakeeper.forms.user import DeleteAccountForm, UploadAvatarForm, CropAvatarForm, \
    EditProfileForm, ChangePasswordForm, \
    ChangeEmailForm, NotificationSettingForm, PrivacySettingForm, ChangeDataForm
from corneakeeper.forms.blog import PostForm
from corneakeeper.extensions import db, avatars
from corneakeeper.utils import generate_token, validate_token, flash_errors, \
    get_file_content, post_processing, redirect_back, \
    rename_image, resize_image, treat
from corneakeeper.emails import send_change_email_email
from corneakeeper.settings import Operations
from corneakeeper.models import User, Photo, Cornea, Post, Category, Comment, \
    CollectPhoto, CollectPost
from corneakeeper.notifications import push_follow_notification
from aip import AipOcr
import datetime as dt

user_bp = Blueprint('user', __name__)


@user_bp.route('/follow/<username>', methods=['POST'])
@login_required
@confirm_required
@permission_required('FOLLOW')
def follow(username):
    user = User.query.filter_by(username=username).first_or_404()
    language = request.cookies.get('language', 'cn')
    if current_user.is_following(user):
        if language == 'cn':
            flash('已经关注过该用户', 'info')
        else:
            flash('Already followed.', 'info')
        return redirect(url_for('.index', username=username))

    current_user.follow(user)
    if language == 'cn':
        flash('关注成功', 'success')
    else:
        flash('User followed.', 'success')
    if user.receive_follow_notification:
        push_follow_notification(follower=current_user, receiver=user)
    return redirect_back()


@user_bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first_or_404()
    if not current_user.is_following(user):
        flash(_('尚未关注过该用户'), 'info')
        return redirect(url_for('.index', username=username))

    current_user.unfollow(user)
    flash(_('取关成功'), 'info')
    return redirect_back()


@user_bp.route('/<username>/photos')
def show_photos(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user == current_user and user.locked:
        flash(_('Your account is locked.'), 'danger')

    if user == current_user and not user.active:
        logout_user()

    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['CK_PHOTO_PER_PAGE']
    pagination = Photo.query.with_parent(user).order_by(
        Photo.timestamp.desc()).paginate(page, per_page)
    photos = pagination.items
    return render_template('user/profile/photos.html', user=user, pagination=pagination, photos=photos)


@user_bp.route('/<username>/collections')
def show_collections(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['CK_PHOTO_PER_PAGE']
    pagination = CollectPhoto.query.with_parent(user).order_by(
        CollectPhoto.timestamp.desc()).paginate(page, per_page)
    collects = pagination.items
    return render_template('user/profile/collections.html', user=user, pagination=pagination, collects=collects)


@user_bp.route('/<username>/followers')
def show_followers(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['CK_USER_PER_PAGE']
    pagination = user.followers.paginate(page, per_page)
    follows = pagination.items
    return render_template('user/profile/followers.html', user=user, pagination=pagination, follows=follows)


@user_bp.route('/<username>/following')
def show_following(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['CK_USER_PER_PAGE']
    pagination = user.following.paginate(page, per_page)
    follows = pagination.items
    return render_template('user/profile/following.html', user=user, pagination=pagination, follows=follows)


@user_bp.route('/<int:photo_id>/recognition', methods=['GET', 'POST'])
def recognition(photo_id):
    photo = Photo.query.filter_by(id=photo_id).first_or_404()
    client = AipOcr(os.getenv('APP_ID'), os.getenv('API_KEY'),
                    os.getenv('BAIDU_SECRET_KEY'))
    path = current_app.config['CK_UPLOAD_PATH'] + '/' + photo.filename
    image = get_file_content(path)
    result = client.basicGeneral(image)
    form = ChangeDataForm()
    if form.validate_on_submit():
        datetime = form.datetime.data
        updatetime = form.updatetime.data
        k1 = form.k1.data
        k2 = form.k2.data
        k_max = form.k_max.data
        thickness_min = form.thickness_min.data
        BSCVA = form.BSCVA.data
        UCVA = form.UCVA.data
        cornea = Cornea(datetime=datetime, updatetime=updatetime, k1=k1, k2=k2,
                        k_max=k_max,
                        thickness_min=thickness_min, BSCVA=BSCVA, UCVA=UCVA)
        db.session.add(cornea)
        db.session.commit()
        flash(_('数据上传成功'), 'success')
        flash('Data created.', 'success')
        return redirect(url_for('user.index', username=current_user.username))
    recognition = post_processing(result)
    form.updatetime.data = dt.datetime.now()
    form.k1.data = recognition['k1']
    form.k2.data = recognition['k2']
    form.k_max.data = recognition['k_max']
    form.thickness_min.data = recognition['thickness_min']
    return render_template('user/profile/recognition.html', form=form)


@user_bp.route('/<username>/diagnosis')  # 诊断函数
def diagnosis(username):
    user = User.query.filter_by(username=username).first_or_404()
    cornea = Cornea.query.filter(Cornea.user_id == current_user.id).order_by(
        'datetime').all()
    language = request.cookies.get('language', 'locale')
    condition = {}
    if cornea:
        k_max, thickness_min, UCVA, BSCVA, k1, k2, IS, myopia, astigmatism = [], [], [], [], [], [], [], [], []
        stage = ''
        for _ in cornea:
            k_max.append(_.k_max)
            thickness_min.append(_.thickness_min)
            UCVA.append(_.UCVA)
            BSCVA.append(_.BSCVA)
            k1.append(_.k1)
            k2.append(_.k2)
            IS.append(abs(_.k1 - _.k2))
            myopia.append(_.myopia)
            astigmatism.append(_.astigmatism)
        progress = (max(k_max) > min(k_max) + 1) and (
                min(thickness_min) * 100 < max(thickness_min) * 98) and (
                           max(myopia) - min(myopia) > 50)
        if language == 'zh':
            # China
            if max(BSCVA) >= 1.0:
                if max(IS) > 1.4:
                    stage = '潜伏期'
                else:
                    stage = '正常'
            elif max(BSCVA) >= 0.8:
                if max(IS) > 1.4:
                    stage = '初发期'
                else:
                    stage = '正常'
            elif max(BSCVA) >= 0.3:
                if min(thickness_min) > 400 and max(k_max) < 53:
                    stage = '完成期 1 级'
                else:
                    stage = '初发期'
            elif max(BSCVA) >= 0.05:
                if min(thickness_min) > 300 and max(k_max) < 55:
                    stage = '完成期 2 级'
                else:
                    stage = '完成期 1 级'
            else:
                if min(thickness_min) <= 300 and max(k_max) > 55:
                    stage = '完成期 3 级'
                else:
                    stage = '完成期 2 级'
        else:
            # Foreign
            if min(thickness_min) >= 400:
                if max(k_max) > 48 and max(myopia) < 500 and max(astigmatism) < 500:
                    stage = 'Early Keratoconus (Stage 1)'
                else:
                    stage = 'Normal'
            elif min(thickness_min) >= 300:
                if max(k_max) > 53:
                    if 800 <= max(myopia) <= 1000 and 800 <= max(astigmatism) <= 1000:
                        stage = 'Advanced Keratoconus (Stage 3)'
                    elif 500 <= max(myopia) < 800 and 500 <= max(astigmatism) < 800:
                        stage = 'Moderate Keratoconus (Stage 2)'
                    else:
                        stage = 'Early Keratoconus (Stage 1)'
                else:
                    stage = 'Normal'
            else:
                if max(k_max) > 55:
                    stage = 'Severe Keratoconus (Stage 4)'
                else:
                    stage = 'Advanced Keratoconus (Stage 3)'
        condition.update(
            stage=stage,
            treatment=treat(stage),
            progress=progress
        )
    return render_template('user/profile/diagnosis.html', user=user, condition=condition)


@user_bp.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.username = form.username.data
        current_user.bio = form.bio.data
        current_user.website = form.website.data
        current_user.location = form.location.data
        db.session.commit()
        flash(_('个人信息更新成功'), 'success')
        return redirect(url_for('.index', username=current_user.username))
    form.name.data = current_user.name
    form.username.data = current_user.username
    form.bio.data = current_user.bio
    form.website.data = current_user.website
    form.location.data = current_user.location
    return render_template('user/settings/edit_profile.html', form=form, user=current_user)


@user_bp.route('/settings/data/<datetime>', methods=['GET', 'POST'])
@login_required
def change_data(datetime):
    cornea = Cornea.query.filter(Cornea.datetime == datetime).one()
    form = ChangeDataForm()
    if form.validate_on_submit():
        cornea.datetime = form.datetime.data
        cornea.updatetime = form.updatetime.data
        cornea.k1 = form.k1.data
        cornea.k2 = form.k2.data
        cornea.k_max = form.k_max.data
        cornea.thickness_min = form.thickness_min.data
        cornea.BSCVA = form.BSCVA.data
        cornea.UCVA = form.UCVA.data
        db.session.commit()
        flash(_('数据更新成功'), 'success')
        return redirect(url_for('.index', username=current_user.username))
    form.datetime.data = cornea.datetime
    form.updatetime.data = dt.datetime.now()
    form.k1.data = cornea.k1
    form.k2.data = cornea.k2
    form.k_max.data = cornea.k_max
    form.thickness_min.data = cornea.thickness_min
    form.BSCVA.data = cornea.BSCVA
    form.UCVA.data = cornea.UCVA
    return render_template('user/settings/change_data.html', form=form)


@user_bp.route('/settings/avatar')
@login_required
@confirm_required
def change_avatar():
    upload_form = UploadAvatarForm()
    crop_form = CropAvatarForm()
    return render_template('user/settings/change_avatar.html', upload_form=upload_form, crop_form=crop_form)


@user_bp.route('/settings/avatar/upload', methods=['POST'])
@login_required
@confirm_required
def upload_avatar():
    form = UploadAvatarForm()
    if form.validate_on_submit():
        image = form.image.data
        filename = avatars.save_avatar(image)
        current_user.avatar_raw = filename
        db.session.commit()
        flash('Image uploaded, please crop.', 'success')
    flash_errors(form)
    return redirect(url_for('.change_avatar'))


@user_bp.route('/settings/avatar/crop', methods=['POST'])
@login_required
@confirm_required
def crop_avatar():
    form = CropAvatarForm()
    if form.validate_on_submit():
        x = form.x.data
        y = form.y.data
        w = form.w.data
        h = form.h.data
        filenames = avatars.crop_avatar(current_user.avatar_raw, x, y, w, h)
        current_user.avatar_s = filenames[0]
        current_user.avatar_m = filenames[1]
        current_user.avatar_l = filenames[2]
        db.session.commit()
        flash('Avatar updated.', 'success')
    flash_errors(form)
    return redirect(url_for('.change_avatar'))


@user_bp.route('/settings/change-email', methods=['GET', 'POST'])
@fresh_login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        token = generate_token(user=current_user,
                               operation=Operations.CHANGE_EMAIL,
                               new_email=form.email.data.lower())
        send_change_email_email(to=form.email.data, user=current_user,
                                token=token)
        flash('Confirm email sent, check your inbox.', 'info')
        return redirect(url_for('.index', username=current_user.username))
    return render_template('user/settings/change_email.html', form=form)


@user_bp.route('/change-email/<token>')
@login_required
def change_email(token):
    if validate_token(user=current_user, token=token,
                      operation=Operations.CHANGE_EMAIL):
        flash(_('邮箱更新成功'), 'success')
        return redirect(url_for('.index', username=current_user.username))
    else:
        flash(_('无效 token 或 token 已过期'), 'warning')
        return redirect(url_for('.change_email_request'))


@user_bp.route('/settings/account/delete', methods=['GET', 'POST'])
@fresh_login_required
def delete_account():
    form = DeleteAccountForm()
    if form.validate_on_submit():
        db.session.delete(current_user._get_current_object())
        db.session.commit()
        flash(_('注销账户成功！'), 'success')
        return redirect(url_for('blog.index'))
    return render_template('user/settings/delete_account.html', form=form)


@user_bp.route('/settings/change-password', methods=['GET', 'POST'])
@fresh_login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.validate_password(form.old_password.data):
            current_user.set_password(form.password.data)
            db.session.commit()
            flash(_('密码已修改'), 'success')
            return redirect(url_for('.index', username=current_user.username))
        else:
            flash(_('密码错误'), 'warning')
    return render_template('user/settings/change_password.html', form=form)


@user_bp.route('/settings/privacy', methods=['GET', 'POST'])
@login_required
def privacy_setting():
    form = PrivacySettingForm()
    if form.validate_on_submit():
        current_user.public_charts = form.public_charts.data
        current_user.public_diagnosis = form.public_diagnosis.data
        current_user.public_collections = form.public_collections.data
        current_user.public_photos = form.public_photos.data
        current_user.public_followings = form.public_followings.data
        current_user.public_followers = form.public_followers.data
        db.session.commit()
        flash(_('隐私设置已更新'), 'success')
        return redirect(url_for('.index', username=current_user.username))
    form.public_charts.data = current_user.public_charts
    form.public_diagnosis.data = current_user.public_diagnosis
    form.public_collections.data = current_user.public_collections
    form.public_photos.data = current_user.public_photos
    form.public_followings.data = current_user.public_followings
    form.public_followers.data = current_user.public_followers
    return render_template('user/settings/edit_privacy.html', form=form)


@user_bp.route('/settings/notification', methods=['GET', 'POST'])
@login_required
def notification_setting():
    form = NotificationSettingForm()
    if form.validate_on_submit():
        current_user.receive_collect_notification = form.receive_collect_notification.data
        current_user.receive_comment_notification = form.receive_comment_notification.data
        current_user.receive_follow_notification = form.receive_follow_notification.data
        db.session.commit()
        flash(_('通知设置已更新'), 'success')
        return redirect(url_for('.index', username=current_user.username))
    form.receive_collect_notification.data = current_user.receive_collect_notification
    form.receive_comment_notification.data = current_user.receive_comment_notification
    form.receive_follow_notification.data = current_user.receive_follow_notification
    return render_template('user/settings/edit_notification.html', form=form)


@user_bp.route('/<username>')
def index(username):
    user = User.query.filter_by(username=username).first_or_404()
    cornea = Cornea.query.filter_by(user=user).all()
    return render_template('user/profile/charts.html', user=user, cornea=cornea)


@user_bp.route('<username>/I-S-Chart')
@login_required
def generate_IS_chart(username):
    user = User.query.filter_by(username=username).first_or_404()
    x, y = [], []
    for cornea in Cornea.query.filter_by(user=user).order_by('datetime').all():
        x.append(cornea.datetime.strftime('%Y-%m-%d'))
        y.append(round(abs(cornea.k1 - cornea.k2), 1))
    line = Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
    line.add_xaxis(x)
    line.add_yaxis(_('角膜屈光力差值'), y)
    line.set_global_opts(
        title_opts=opts.TitleOpts(title=_('角膜屈光力差值变化图'),
                                  title_textstyle_opts=opts.TextStyleOpts(font_family='SimSun')),
        legend_opts=opts.LegendOpts(textstyle_opts=opts.TextStyleOpts(font_family='SimSun')),
        xaxis_opts=opts.AxisOpts(axislabel_opts={'rotate': 30 if len(x) > 3 else 0}))
    return line.dump_options_with_quotes()


@user_bp.route('<username>/K-Chart')
@login_required
def generate_K_chart(username):
    user = User.query.filter_by(username=username).first_or_404()
    x, y_k_max = [], []
    for cornea in Cornea.query.filter_by(user=user).order_by('datetime').all():
        x.append(cornea.datetime.strftime('%Y-%m-%d'))  # 转字符串
        y_k_max.append(cornea.k_max)
    line = Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
    line.add_xaxis(x)
    line.add_yaxis(_('最大曲率'), y_k_max)
    line.set_global_opts(title_opts=opts.TitleOpts(title=_('最大曲率变化图'), title_textstyle_opts=opts.TextStyleOpts(
        font_family='SimSun')),
                         legend_opts=opts.LegendOpts(textstyle_opts=opts.TextStyleOpts(font_family='SimSun')),
                         xaxis_opts=opts.AxisOpts(axislabel_opts={'rotate': 30 if len(x) > 3 else 0}))
    return line.dump_options_with_quotes()


@user_bp.route('<username>/Thickness-Chart')
@login_required
def generate_thickness_chart(username):
    user = User.query.filter_by(username=username).first_or_404()
    x, y = [], []
    for cornea in Cornea.query.filter_by(user=user).order_by('datetime').all():
        x.append(cornea.datetime.strftime('%Y-%m-%d'))  # 转字符串
        y.append(cornea.thickness_min)
    line = Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
    line.add_xaxis(x)
    line.add_yaxis(_('最薄点厚度'), y)
    line.set_global_opts(
        title_opts=opts.TitleOpts(title=_('最薄点厚度变化图'),
                                  title_textstyle_opts=opts.TextStyleOpts(font_family='SimSun')),
        legend_opts=opts.LegendOpts(textstyle_opts=opts.TextStyleOpts(font_family='SimSun')),
        xaxis_opts=opts.AxisOpts(axislabel_opts={'rotate': 30 if len(x) > 3 else 0}))
    return line.dump_options_with_quotes()


@user_bp.route('<username>/VisualAcuity-Chart')
@login_required
def generate_visualAcuity_chart(username):
    user = User.query.filter_by(username=username).first_or_404()
    x, y_1, y_2 = [], [], []
    for cornea in Cornea.query.filter_by(user=user).order_by('datetime').all():
        x.append(cornea.datetime.strftime('%Y-%m-%d'))  # 转字符串
        y_1.append(cornea.BSCVA)  # 转字符串
        y_2.append(cornea.UCVA)
    line = Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
    line.add_xaxis(x)
    line.add_yaxis(_('最佳眼镜矫正视力'), y_1)
    line.add_yaxis(_('裸眼视力'), y_2)
    line.set_global_opts(
        title_opts=opts.TitleOpts(title=_('视力变化图'),
                                  title_textstyle_opts=opts.TextStyleOpts(font_family='SimSun')),
        legend_opts=opts.LegendOpts(textstyle_opts=opts.TextStyleOpts(font_family='SimSun')),
        xaxis_opts=opts.AxisOpts(axislabel_opts={'rotate': 30 if len(x) > 3 else 0}))
    return line.dump_options_with_quotes()


@user_bp.route('<username>/Myopia-Chart')
@login_required
def generate_myopia_chart(username):
    user = User.query.filter_by(username=username).first_or_404()
    x, y = [], []
    for _ in Cornea.query.filter_by(user=user).order_by('datetime').all():
        x.append(_.datetime.strftime('%Y-%m-%d'))
        y.append(_.myopia)
    line = Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
    line.add_xaxis(x)
    line.add_yaxis(_('近视度数'), y)
    line.set_global_opts(
        title_opts=opts.TitleOpts(title=_('近视度数变化图'),
                                  title_textstyle_opts=opts.TextStyleOpts(font_family='SimSun')),
        legend_opts=opts.LegendOpts(textstyle_opts=opts.TextStyleOpts(font_family='SimSun')),
        xaxis_opts=opts.AxisOpts(axislabel_opts={'rotate': 30 if len(x) > 3 else 0}))
    return line.dump_options_with_quotes()


@user_bp.route('<username>/Astigmatism-Chart')
@login_required
def generate_astigmatism_chart(username):
    user = User.query.filter_by(username=username).first_or_404()
    x, y = [], []
    for cornea in Cornea.query.filter_by(user=user).order_by('datetime').all():
        x.append(cornea.datetime.strftime('%Y-%m-%d'))
        y.append(cornea.astigmatism)
    line = Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
    line.add_xaxis(x)
    line.add_yaxis(_('散光度数'), y)
    line.set_global_opts(
        title_opts=opts.TitleOpts(title=_('散光度数变化图'),
                                  title_textstyle_opts=opts.TextStyleOpts(font_family='SimSun')),
        legend_opts=opts.LegendOpts(textstyle_opts=opts.TextStyleOpts(font_family='SimSun')),
        xaxis_opts=opts.AxisOpts(axislabel_opts={'rotate': 30 if len(x) > 3 else 0}))
    return line.dump_options_with_quotes()


@user_bp.route('settings/history')
@login_required
def history():
    cornea = Cornea.query.filter(Cornea.user_id == current_user.id).order_by(
        Cornea.datetime.desc()).all()
    return render_template('user/settings/history.html', cornea=cornea)


# 论坛管理

# 文章管理
@user_bp.route('<username>/post/manage')
@login_required
@permission_required('MANAGE')
def manage_post(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user != current_user:
        abort(403)
    page = request.args.get('page', 1, type=int)
    if user.is_admin:
        pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
            page, per_page=current_app.config['BLOG_MANAGE_POST_PER_PAGE'])
    else:
        pagination = Post.query.filter_by(user=user).order_by(
            Post.timestamp.desc()).paginate(
            page, per_page=current_app.config['BLOG_MANAGE_POST_PER_PAGE'])
    posts = pagination.items
    return render_template('user/forum/manage_post.html', user=user, page=page, pagination=pagination, posts=posts)


# 发布文章
@user_bp.route('<username>/post/new', methods=['GET', 'POST'])
@login_required
@permission_required('CREATE')
def new_post(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        title = form.title.data
        body = form.body.data
        category = Category.query.get(form.category.data)
        post = Post(title=title, body=body, category=category, user=user)
        db.session.add(post)
        db.session.commit()
        flash(_('文章发布成功'), 'success')
        return redirect(url_for('blog.show_post', post_id=post.id))
    return render_template('user/forum/new_post.html', form=form)


# 修改文章
@user_bp.route('<username>/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('MANAGE')
def edit_post(username, post_id):
    user = User.query.filter_by(username=username).first_or_404()
    if user != current_user:
        abort(403)
    form = PostForm()
    post = Post.query.get_or_404(post_id)
    if form.validate_on_submit():
        post.title = form.title.data
        post.body = form.body.data
        post.category = Category.query.get(form.category.data)
        db.session.commit()
        flash(_('文章修改成功'), 'success')
        return redirect(url_for('blog.show_post', post_id=post.id))
    form.title.data = post.title
    form.body.data = post.body
    form.category.data = post.category_id
    return render_template('user/forum/edit_post.html', form=form)


# 删除文章
@user_bp.route('<username>/post/<int:post_id>/delete', methods=['POST'])
@login_required
@permission_required('MANAGE')
def delete_post(username, post_id):
    user = User.query.filter_by(username=username).first_or_404()
    if user != current_user:
        abort(403)
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash(_('文章删除成功'), 'success')
    return redirect_back()


# 设置文章评论
@user_bp.route('<username>/post/<int:post_id>/set-comment', methods=['POST'])
@login_required
@permission_required('MANAGE')
def set_comment(username, post_id):
    user = User.query.filter_by(username=username).first_or_404()
    if user != current_user:
        abort(403)
    post = Post.query.get_or_404(post_id)
    if post.can_comment:
        post.can_comment = False
        flash(_('评论已禁止'), 'success')
    else:
        post.can_comment = True
        flash(_('评论已开放'), 'success')
    db.session.commit()
    return redirect_back()


# 管理评论
@user_bp.route('<username>/comment/manage')
@login_required
@permission_required('MANAGE')
def manage_comment(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user != current_user:
        abort(403)
    filter_rule = request.args.get('filter', 'all')  # 'all', 'unreviewed', 'admin'
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['BLOG_COMMENT_PER_PAGE']
    if user.is_admin:
        if filter_rule == 'unread':
            # 别人给管理员的评论未读
            filtered_comments = Comment.query.join(Post).filter(
                and_(Comment.reviewed is False, Post.user_id == user.id,
                     Comment.user_id != user.id))
        elif filter_rule == 'myself':
            filtered_comments = Comment.query.filter_by(from_admin=True)
        else:
            # 所有其他人人的评论
            filtered_comments = Comment.query.filter(Comment.user_id != user.id)
    else:
        if filter_rule == 'unread':
            # 别人给自己的评论未读
            filtered_comments = Comment.query.join(Post).filter(
                and_(Comment.reviewed is False, Post.user_id == user.id,
                     Comment.user_id != user.id))
        elif filter_rule == 'myself':
            # 自己写的评论
            filtered_comments = Comment.query.filter(Comment.user_id == user.id)
        else:
            # 所有来自他人的评论
            filtered_comments = Comment.query.join(Post,
                                                   Comment.post_id == Post.id).filter(
                and_(Post.user_id == user.id, Comment.user_id != user.id))
    pagination = filtered_comments.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=per_page)
    comments = pagination.items
    return render_template('user/forum/manage_comment.html', comments=comments, pagination=pagination, user=user)


# 同意评论公开
@user_bp.route('<username>/comment/<int:comment_id>/approve', methods=['POST'])
@login_required
@permission_required('MANAGE')
def approve_comment(username, comment_id):
    user = User.query.filter_by(username=username).first_or_404()
    if user != current_user:
        abort(403)
    comment = Comment.query.get_or_404(comment_id)
    comment.reviewed = True
    db.session.commit()
    flash(_('评论已公开'), 'success')
    return redirect_back()


# 删除评论
@user_bp.route('<username>/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
@permission_required('MANAGE')
def delete_comment(username, comment_id):
    user = User.query.filter_by(username=username).first_or_404()
    if user != current_user:
        abort(403)
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    flash(_('评论已删除'), 'success')
    return redirect_back()


@user_bp.route('<username>/collect/manage')
@login_required
@permission_required('MANAGE')
def manage_collect(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user != current_user:
        abort(403)
    page = request.args.get('page', 1, type=int)
    pagination = CollectPost.query.with_parent(user).order_by(
        Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['BLOG_MANAGE_POST_PER_PAGE'])
    posts = pagination.items
    return render_template('user/forum/manage_collect.html', user=user, page=page, pagination=pagination, posts=posts)


# 上传数据
@user_bp.route('/manual-upload', methods=['GET', 'POST'])
@login_required
@confirm_required
@permission_required('UPLOAD')
def manual_upload():
    form = ChangeDataForm()
    if form.validate_on_submit():
        datetime = form.datetime.data
        updatetime = form.updatetime.data
        k1 = form.k1.data
        k2 = form.k2.data
        k_max = form.k_max.data
        thickness_min = form.thickness_min.data
        BSCVA = form.BSCVA.data
        UCVA = form.UCVA.data
        cornea = Cornea(datetime=datetime, updatetime=updatetime, k1=k1, k2=k2,
                        k_max=k_max,
                        thickness_min=thickness_min, BSCVA=BSCVA, UCVA=UCVA,
                        user=current_user._get_current_object())
        db.session.add(cornea)
        db.session.commit()
        flash(_('数据上传成功'), 'success')
        return redirect(url_for('user.index', username=current_user.username))
    return render_template('user/profile/manual_upload.html', form=form)


# 图片上传
@user_bp.route('/photo-upload', methods=['GET', 'POST'])
@login_required
@confirm_required
@permission_required('UPLOAD')
def photo_upload():
    if request.method == 'POST' and 'file' in request.files:
        f = request.files.get('file')
        filename = rename_image(f.filename)
        f.save(os.path.join(current_app.config['CK_UPLOAD_PATH'], filename))
        filename_s = resize_image(f, filename,
                                  current_app.config['CK_PHOTO_SIZE']['small'])
        filename_m = resize_image(f, filename,
                                  current_app.config['CK_PHOTO_SIZE']['medium'])
        photo = Photo(
            filename=filename,
            filename_s=filename_s,
            filename_m=filename_m,
            user=current_user._get_current_object()
        )
        db.session.add(photo)
        db.session.commit()
    return render_template('user/profile/photo_upload.html')


# 删除角膜数据
@user_bp.route('/corneadata/<datetime>/delete', methods=['POST'])
@login_required
@permission_required('MANAGE')
def delete_corneadata(datetime):
    cornea = Cornea.query.filter(and_(Cornea.datetime == datetime, Cornea.user_id == current_user.id)).first()
    db.session.delete(cornea)
    db.session.commit()
    flash(_('数据删除成功'), 'success')
    return redirect_back()
