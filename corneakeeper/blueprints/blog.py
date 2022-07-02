from flask import render_template, flash, redirect, url_for, request, \
    current_app, Blueprint, abort, make_response
from flask_login import current_user, login_required
from flask_babel import _
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
    return render_template('blog/index.html', pagination=pagination, posts=posts)


@blog_bp.route('/about')
def about():
    return render_template('blog/about.html')


@blog_bp.route('/category/<int:category_id>')
def show_category(category_id):
    category = Category.query.get_or_404(category_id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['BLOG_POST_PER_PAGE']
    pagination = Post.query.with_parent(category).order_by(
        Post.timestamp.desc()).paginate(page, per_page)
    posts = pagination.items
    return render_template('blog/category.html', category=category, pagination=pagination, posts=posts)


@blog_bp.route('/post/<int:post_id>', methods=['GET', 'POST'])
def show_post(post_id):
    post = Post.query.get_or_404(post_id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['BLOG_COMMENT_PER_PAGE']
    pagination = Comment.query.with_parent(post).filter_by(
        reviewed=True).order_by(Comment.timestamp.asc()).paginate(
        page, per_page)
    comments = pagination.items
    if current_user.is_authenticated:
        form = UserCommentForm()
        user = User.query.filter_by(username=post.user.username).first_or_404()
        form.author.data = current_user.name
        form.email.data = current_user.email
        form.site.data = current_user.website
        from_admin = current_user.is_admin
        reviewed = True if user.id == current_user.id else False  # 判断是否为作者本人
    else:
        form = CommentForm()
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
            send_new_reply_email(template='emails/new_reply', comment=replied_comment)
        db.session.add(comment)
        db.session.commit()
        if current_user.is_authenticated:  # send message based on authentication status
            if current_user.id == post.user_id:
                flash(_('评论发布成功'), 'success')
            else:
                flash(_('您的评论将会在审核后公布'), 'info')
                send_new_comment_email(template='emails/new_comment', post=post)
        else:
            flash(_('您的评论将会在审核后公布'), 'info')
            send_new_comment_email(template='emails/new_comment', post=post)
        return redirect(url_for('.show_post', post_id=post_id))
    return render_template('blog/post.html', post=post, pagination=pagination, form=form, comments=comments)


@blog_bp.route('/collect/<int:post_id>', methods=['POST'])
@login_required
@confirm_required
@permission_required('COLLECT')
def collect(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user.is_collecting_post(post):
        flash(_('已经添加过收藏'), 'info')
        return redirect(url_for('blog.show_post', post_id=post_id))

    current_user.collect_post(post)
    flash(_('文章已收藏'), 'success')
    if current_user != post.user and post.user.receive_collect_notification:
        push_collect_post_notification(collector=current_user, post_id=post_id,
                                       receiver=post.user)
    return redirect(url_for('blog.show_post', post_id=post_id))


@blog_bp.route('/uncollect/<int:post_id>', methods=['POST'])
@login_required
def uncollect(post_id):
    post = Post.query.get_or_404(post_id)
    if not current_user.is_collecting_post(post):
        flash(_('文章尚未收藏'), 'info')
        return redirect(url_for('blog.show_post', post_id=post_id))

    current_user.uncollect_post(post)
    flash(_('文章已取消收藏'), 'info')
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


@blog_bp.route('/set-locale/<locale>')
def set_locale(locale):
    if locale not in current_app.config['CK_LOCALES']:
        abort(404)
    response = make_response(redirect_back())
    response.set_cookie('locale', locale, max_age=60 * 60 * 24 * 30)
    if current_user.is_authenticated:
        current_user.locale = locale
        db.session.commit()
    return response


# 搜索功能
@blog_bp.route('/search')
def search():
    keywords = request.args.get('keywords', '').strip()
    if keywords == '':
        flash(_('请输入关键字'), 'warning')
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
    return render_template('blog/search.html', keywords=keywords, results=results,
                           pagination=pagination, category=category)
