from flask import render_template, flash, redirect, url_for, request, Blueprint
from flask_login import login_required

from corneakeeper.extensions import db
from corneakeeper.forms.admin import CategoryForm, LinkForm
from corneakeeper.models import Category, Link

from corneakeeper.decorators import permission_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/category/manage')
@login_required
@permission_required('ADMINISTER')
def manage_category():
    return render_template('admin/manage_category_{}.html'.format(request.cookies.get('language', 'cn')))


@admin_bp.route('/category/new', methods=['GET', 'POST'])
@login_required
@permission_required('ADMINISTER')
def new_category():
    form = CategoryForm()
    language = request.cookies.get('language', 'cn')
    if language == 'cn':
        form.name.label.text = '分类名'
        form.submit.label.text = '提交'
    if form.validate_on_submit():
        name = form.name.data
        category = Category(name=name)
        db.session.add(category)
        db.session.commit()
        if language == 'cn':
            flash('分类创建成功', 'success')
        else:
            flash('Category created.', 'success')
        return redirect(url_for('.manage_category'))
    return render_template('admin/new_category_{}.html'.format(language), form=form)


@admin_bp.route('/category/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('ADMINISTER')
def edit_category(category_id):
    form = CategoryForm()
    language = request.cookies.get('language', 'cn')
    if language == 'cn':
        form.name.label.text = '分类名'
        form.submit.label.text = '提交'
    category = Category.query.get_or_404(category_id)
    if category.id == 1:
        if language == 'cn':
            flash('你无法修改默认分类', 'warning')
        else:
            flash('You can not edit the default category.', 'warning')
        return redirect(url_for('blog.index'))
    if form.validate_on_submit():
        category.name = form.name.data
        db.session.commit()
        if language == 'cn':
            flash('分类修改成功', 'success')
        else:
            flash('Category updated.', 'success')
        return redirect(url_for('admin.manage_category'))
    form.name.data = category.name
    return render_template('admin/edit_category_{}.html'.format(language), form=form)


@admin_bp.route('/category/<int:category_id>/delete', methods=['POST'])
@login_required
@permission_required('ADMINISTER')
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    language = request.cookies.get('language', 'cn')
    if category.id == 1:
        if language == 'cn':
            flash('你不能删除默认分类', 'warning')
        else:
            flash('You can not delete the default category.', 'warning')
        return redirect(url_for('blog.index'))
    category.delete()
    if language == 'cn':
        flash('分类已删除', 'success')
    else:
        flash('Category deleted.', 'success')
    return redirect(url_for('.manage_category'))


@admin_bp.route('/link/manage')
@login_required
@permission_required('ADMINISTER')
def manage_link():
    return render_template('admin/manage_link_{}.html'.format(request.cookies.get('language', 'cn')))


@admin_bp.route('/link/new', methods=['GET', 'POST'])
@login_required
@permission_required('ADMINISTER')
def new_link():
    form = LinkForm()
    language = request.cookies.get('language', 'cn')
    if language == 'cn':
        form.name.label.text = '链接名'
        form.url.label.text = '链接地址'
        form.submit.label.text = '提交'
    if form.validate_on_submit():
        name = form.name.data
        url = form.url.data
        link = Link(name=name, url=url)
        db.session.add(link)
        db.session.commit()
        if language == 'cn':
            flash('链接创建成功', 'success')
        else:
            flash('Link created.', 'success')
        return redirect(url_for('.manage_link'))
    return render_template('admin/new_link_{}.html'.format(language), form=form)


@admin_bp.route('/link/<int:link_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('ADMINISTER')
def edit_link(link_id):
    form = LinkForm()
    language = request.cookies.get('language', 'cn')
    if language == 'cn':
        form.name.label.text = '链接名'
        form.url.label.text = '链接地址'
        form.submit.label.text = '提交'
    link = Link.query.get_or_404(link_id)
    if form.validate_on_submit():
        link.name = form.name.data
        link.url = form.url.data
        db.session.commit()
        if language == 'cn':
            flash('链接已修改', 'success')
        else:
            flash('Link updated.', 'success')
        return redirect(url_for('.manage_link'))
    form.name.data = link.name
    form.url.data = link.url
    return render_template('admin/edit_link_{}.html'.format(language), form=form)


@admin_bp.route('/link/<int:link_id>/delete', methods=['POST'])
@login_required
@permission_required('ADMINISTER')
def delete_link(link_id):
    link = Link.query.get_or_404(link_id)
    db.session.delete(link)
    db.session.commit()
    flash('Link deleted.', 'success')
    return redirect(url_for('.manage_link'))

# @admin_bp.route('/uploads/<path:filename>')
# def get_image(filename):
#     return send_from_directory(current_app.config['BLUELOG_UPLOAD_PATH'], filename)
#
#
# @admin_bp.route('/upload', methods=['POST'])
# def upload_image():
#     f = request.files.get('upload')
#     if not allowed_file(f.filename):
#         return upload_fail('Image only!')
#     f.save(os.path.join(current_app.config['BLUELOG_UPLOAD_PATH'], f.filename))
#     url = url_for('.get_image', filename=f.filename)
#     return upload_success(url, f.filename)
