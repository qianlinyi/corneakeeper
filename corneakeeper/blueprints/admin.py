from flask import render_template, flash, redirect, url_for, request, Blueprint
from flask_login import login_required
from flask_babel import _
from corneakeeper.extensions import db
from corneakeeper.forms.admin import CategoryForm, LinkForm
from corneakeeper.models import Category, Link

from corneakeeper.decorators import permission_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/category/manage')
@login_required
@permission_required('ADMINISTER')
def manage_category():
    return render_template('admin/manage_category.html')


@admin_bp.route('/category/new', methods=['GET', 'POST'])
@login_required
@permission_required('ADMINISTER')
def new_category():
    form = CategoryForm()
    if form.validate_on_submit():
        name = form.name.data
        category = Category(name=name)
        db.session.add(category)
        db.session.commit()
        flash(_('分类创建成功'), 'success')
        return redirect(url_for('.manage_category'))
    return render_template('admin/new_category.html', form=form)


@admin_bp.route('/category/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('ADMINISTER')
def edit_category(category_id):
    form = CategoryForm()
    category = Category.query.get_or_404(category_id)
    if category.id == 1:
        flash(_('你无法修改默认分类'), 'warning')
        return redirect(url_for('blog.index'))
    if form.validate_on_submit():
        category.name = form.name.data
        db.session.commit()
        flash(_('分类修改成功'), 'success')
        return redirect(url_for('admin.manage_category'))
    form.name.data = category.name
    return render_template('admin/edit_category.html', form=form)


@admin_bp.route('/category/<int:category_id>/delete', methods=['POST'])
@login_required
@permission_required('ADMINISTER')
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    if category.id == 1:
        flash(_('你不能删除默认分类'), 'warning')
        return redirect(url_for('blog.index'))
    category.delete()
    flash(_('分类已删除'), 'success')
    return redirect(url_for('.manage_category'))


@admin_bp.route('/link/manage')
@login_required
@permission_required('ADMINISTER')
def manage_link():
    return render_template('admin/manage_link.html')


@admin_bp.route('/link/new', methods=['GET', 'POST'])
@login_required
@permission_required('ADMINISTER')
def new_link():
    form = LinkForm()
    if form.validate_on_submit():
        name = form.name.data
        url = form.url.data
        link = Link(name=name, url=url)
        db.session.add(link)
        db.session.commit()
        flash(_('链接创建成功'), 'success')
        return redirect(url_for('.manage_link'))
    return render_template('admin/new_link.html', form=form)


@admin_bp.route('/link/<int:link_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('ADMINISTER')
def edit_link(link_id):
    form = LinkForm()
    link = Link.query.get_or_404(link_id)
    if form.validate_on_submit():
        link.name = form.name.data
        link.url = form.url.data
        db.session.commit()
        flash(_('链接已修改'), 'success')
        return redirect(url_for('.manage_link'))
    form.name.data = link.name
    form.url.data = link.url
    return render_template('admin/edit_link.html', form=form)


@admin_bp.route('/link/<int:link_id>/delete', methods=['POST'])
@login_required
@permission_required('ADMINISTER')
def delete_link(link_id):
    link = Link.query.get_or_404(link_id)
    db.session.delete(link)
    db.session.commit()
    flash(_('链接已删除'), 'success')
    return redirect(url_for('.manage_link'))
