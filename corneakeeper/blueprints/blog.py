"""
    :author: Linyi Qian (钱霖奕)
    :copyright: © 2022 Linyi Qian <qianlinyi@hhu.edu.cn>
    :license: MIT, see LICENSE for more details.
"""
from flask import render_template, flash, redirect, url_for, request, \
    current_app, Blueprint, abort, make_response
from flask_login import current_user, login_required

from corneakeeper.emails import send_new_comment_email, send_new_reply_email
from corneakeeper.extensions import db
from corneakeeper.forms.blog import CommentForm, UserCommentForm
from corneakeeper.models import Post, Category, Comment, User, Tag, Photo
from corneakeeper.utils import redirect_back
from corneakeeper.notifications import push_collect_post_notification
from corneakeeper.decorators import confirm_required, permission_required

blog_bp = Blueprint('blog', __name__)


@blog_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['BLOG_POST_PER_PAGE']
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(page,
                                                                     per_page=per_page)
    posts = pagination.items
    return render_template(
        'blog/index_{}.html'.format(request.cookies.get('language', 'cn')),
        pagination=pagination,
        posts=posts)


@blog_bp.route('/about')
def about():
    return render_template(
        'blog/about_{}.html'.format(request.cookies.get('language', 'cn')))


@blog_bp.route('/category/<int:category_id>')
def show_category(category_id):
    category = Category.query.get_or_404(category_id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['BLOG_POST_PER_PAGE']
    pagination = Post.query.with_parent(category).order_by(
        Post.timestamp.desc()).paginate(page, per_page)
    posts = pagination.items
    return render_template(
        'blog/category_{}.html'.format(request.cookies.get('language', 'cn')),
        category=category,
        pagination=pagination, posts=posts)


@blog_bp.route('/post/<int:post_id>', methods=['GET', 'POST'])
def show_post(post_id):
    post = Post.query.get_or_404(post_id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['BLOG_COMMENT_PER_PAGE']
    pagination = Comment.query.with_parent(post).filter_by(
        reviewed=True).order_by(Comment.timestamp.asc()).paginate(
        page, per_page)
    comments = pagination.items
    language = request.cookies.get('language', 'cn')
    if current_user.is_authenticated:
        form = UserCommentForm()
        user = User.query.filter_by(username=post.user.username).first_or_404()
        if language == 'cn':
            form.body.label.text = '内容'
            form.submit.label.text = '提交'
        form.author.data = current_user.name
        form.email.data = current_user.email
        form.site.data = current_user.website
        from_admin = current_user.is_admin
        reviewed = True if user.id == current_user.id else False  # 判断是否为作者本人
    else:
        form = CommentForm()
        if language == 'cn':
            form.author.label.text = '昵称'
            form.email.label.text = '邮箱'
            form.site.label.text = '网址'
            form.body.label.text = '内容'
            form.submit.label.text = '提交'
        from_admin = False
        reviewed = False

    if form.validate_on_submit():
        author = form.author.data
        email = form.email.data
        site = form.site.data
        body = form.body.data
        if current_user.is_authenticated:
            comment = Comment(
                author=author, email=email, site=site, body=body,
                from_admin=from_admin, post=post, reviewed=reviewed,
                user=User.query.filter_by(
                    username=current_user.username).first_or_404())
        else:
            comment = Comment(
                author=author, email=email, site=site, body=body,
                from_admin=from_admin, post=post, reviewed=reviewed)
        replied_id = request.args.get('reply')
        if replied_id:
            replied_comment = Comment.query.get_or_404(replied_id)
            comment.replied = replied_comment
            send_new_reply_email(
                template='emails/new_reply_{}'.format(language),
                comment=replied_comment)
        db.session.add(comment)
        db.session.commit()
        if current_user.is_authenticated:  # send message based on authentication status
            if current_user.id == post.user_id:
                if language == 'cn':
                    flash('评论发布成功', 'success')
                else:
                    flash('Comment published.', 'success')
            else:
                if language == 'cn':
                    flash('您的评论将会在审核后公布', 'info')
                else:
                    flash(
                        'Thanks, your comment will be published after reviewed.',
                        'info')
                send_new_comment_email(
                    template='emails/new_comment_{}'.format(language),
                    post=post)  # send notification email to admin
        else:
            if language == 'cn':
                flash('您的评论将会在审核后公布', 'info')
            else:
                flash('Thanks, your comment will be published after reviewed.',
                      'info')
            send_new_comment_email(
                template='emails/new_comment_{}'.format(language),
                post=post)  # send notification email to admin
        return redirect(url_for('.show_post', post_id=post_id))
    return render_template('blog/post_{}.html'.format(language), post=post,
                           pagination=pagination, form=form,
                           comments=comments)


@blog_bp.route('/collect/<int:post_id>', methods=['POST'])
@login_required
@confirm_required
@permission_required('COLLECT')
def collect(post_id):
    post = Post.query.get_or_404(post_id)
    language = request.cookies.get('language', 'cn')
    if current_user.is_collecting_post(post):
        if language == 'cn':
            flash('已经添加过收藏', 'info')
        else:
            flash('Already collected.', 'info')
        return redirect(url_for('blog.show_post', post_id=post_id))

    current_user.collect_post(post)
    if language == 'cn':
        flash('文章已收藏', 'success')
    else:
        flash('Photo collected.', 'success')
    if current_user != post.user and post.user.receive_collect_notification:
        push_collect_post_notification(collector=current_user, post_id=post_id,
                                       receiver=post.user)
    return redirect(url_for('blog.show_post', post_id=post_id))


@blog_bp.route('/uncollect/<int:post_id>', methods=['POST'])
@login_required
def uncollect(post_id):
    post = Post.query.get_or_404(post_id)
    language = request.cookies.get('language', 'cn')
    if not current_user.is_collecting_post(post):
        if language == 'cn':
            flash('文章尚未收藏', 'info')
        else:
            flash('Not collect yet.', 'info')
        return redirect(url_for('blog.show_post', post_id=post_id))

    current_user.uncollect_post(post)
    if language == 'cn':
        flash('文章已取消收藏', 'info')
    else:
        flash('Photo uncollected.', 'info')
    return redirect(url_for('blog.show_post', post_id=post_id))


@blog_bp.route('/reply/comment/<int:comment_id>')
def reply_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if not comment.post.can_comment:
        flash('Comment is disabled.', 'warning')
        return redirect(url_for('.show_post', post_id=comment.post.id))
    return redirect(
        url_for('.show_post', post_id=comment.post_id, reply=comment_id,
                author=comment.author) + '#comment-form')


@blog_bp.route('/change-theme/<theme_name>')
def change_theme(theme_name):
    if theme_name not in current_app.config['MW_THEMES'].keys():
        abort(404)
    response = make_response(redirect_back())
    response.set_cookie('theme', theme_name, max_age=30 * 24 * 60 * 60)
    return response


@blog_bp.route('/change-language/<language>')
def change_language(language):
    if language not in current_app.config['MW_LANGUAGE'].keys():
        abort(404)
    response = make_response(redirect_back())
    response.set_cookie('language', language, max_age=30 * 24 * 60 * 60)
    return response


@blog_bp.route('/set-locale/<locale>')
def set_locale(locale):
    if locale not in current_app.config['CK_LOCALES']:
        abort(404)

    response = make_response(redirect_back())
    if current_user.is_authenticated:
        current_user.locale = locale
        db.session.commit()
    else:
        response.set_cookie('locale', locale, max_age=60 * 60 * 24 * 30)
    return response


# 搜索功能
@blog_bp.route('/search')
def search():
    keywords = request.args.get('keywords', '').strip()
    language = request.cookies.get('language', 'cn')
    if keywords == '':
        if language == 'cn':
            flash('请输入关键字', 'warning')
        else:
            flash('Enter keyword about photo, user or tag.', 'warning')
        return redirect_back()

    category = request.args.get('category', 'post')
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['SEARCH_RESULT_PER_PAGE']
    if category == 'post':
        pagination = Post.query.whooshee_search(keywords).paginate(page,
                                                                   per_page)
    elif category == 'user':
        pagination = User.query.whooshee_search(keywords).paginate(page,
                                                                   per_page)
    elif category == 'tag':
        pagination = Tag.query.whooshee_search(keywords).paginate(page,
                                                                  per_page)
    else:
        pagination = Photo.query.whooshee_search(keywords).paginate(page,
                                                                    per_page)
    results = pagination.items
    return render_template('blog/search_{}.html'.format(language),
                           keywords=keywords, results=results,
                           pagination=pagination, category=category)
