import os
import click
from sqlalchemy import and_
from flask import Flask, render_template, current_app
from flask_login import current_user
from flask_wtf.csrf import CSRFError

from corneakeeper.extensions import login_manager, bootstrap, db, moment, mail, ckeditor, csrf, dropzone, avatars, \
    whooshee, babel
from corneakeeper.blueprints.auth import auth_bp
from corneakeeper.blueprints.blog import blog_bp
from corneakeeper.blueprints.admin import admin_bp
from corneakeeper.blueprints.user import user_bp
from corneakeeper.blueprints.main import main_bp
from corneakeeper.blueprints.ajax import ajax_bp
from corneakeeper.settings import config
from corneakeeper.models import User, Post, Category, Comment, Link, Role
from corneakeeper.utils import del_files


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')
    app = Flask('corneakeeper')
    app.jinja_env.add_extension('jinja2.ext.loopcontrols')  # jinja2 循环控制
    app.config.from_object(config[config_name])
    register_extensions(app)  # 注册拓展（拓展初始化）
    register_blueprints(app)  # 注册蓝本
    register_template_context(app)  # 注册模板上下文处理函数
    register_commands(app)  # 注册自定义 shell 命令
    register_errorhandlers(app)
    return app


# 注册拓展（拓展初始化）
def register_extensions(app):
    login_manager.init_app(app)
    bootstrap.init_app(app)
    db.init_app(app)
    moment.init_app(app)
    mail.init_app(app)
    ckeditor.init_app(app)
    csrf.init_app(app)
    dropzone.init_app(app)
    avatars.init_app(app)
    whooshee.init_app(app)
    babel.init_app(app)


def register_blueprints(app):
    app.register_blueprint(blog_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(main_bp, url_prefix='/main')
    app.register_blueprint(ajax_bp, url_prefix='/ajax')


def register_template_context(app):
    @app.context_processor
    def make_template_context():
        admin = User.query.first()
        categories = Category.query.order_by(Category.name).all()
        links = Link.query.order_by(Link.name).all()
        if current_user.is_authenticated:
            if current_user.can('MANAGE'):
                unread_comments = Comment.query.join(Post).filter(
                    and_(Comment.reviewed is False, Post.user_id == current_user.id,
                         Comment.user_id != current_user.id)).count()
            else:
                unread_comments = None
        else:
            unread_comments = None
        return dict(
            admin=admin, categories=categories,
            links=links, unread_comments=unread_comments)


def register_commands(app):
    #  删除表和数据库后进行重建
    @app.cli.command()
    @click.option('--drop', is_flag=True, help='Create after drop.')
    def initdb(drop):
        """Initialize the database."""
        if drop:
            click.confirm('This operation will delete the database, do you want to continue?', abort=True)
            db.drop_all()
            click.echo('Drop tables.')
        db.create_all()
        click.echo('Initialized database.')

    @app.cli.command()
    @click.option('--user', default=10, help='Quantity of users, default is 10.')
    @click.option('--category', default=10, help='Quantity of categories, default is 10.')
    @click.option('--post', default=5, help='Quantity of posts, default is 50.')
    @click.option('--comment', default=20, help='Quantity of comments, default is 500.')
    @click.option('--cornea', default=10, help='Quantity of corneas, default is 10.')
    def forge(user, category, post, comment, cornea):
        """Generate fake data."""
        from corneakeeper.fakes import fake_admin, fake_categories, fake_posts, fake_comments, fake_links, fake_user, \
            fake_corneas

        click.echo('Delete all tha avatars...')
        del_files(os.path.join(current_app.config['CK_UPLOAD_PATH'], 'avatars'))

        db.drop_all()
        db.create_all()

        click.echo('Initializing the roles and permissions...')
        Role.init_role()

        click.echo('Generating the administrator...')
        fake_admin()

        click.echo('Generating %d users...' % user)
        fake_user(user)

        click.echo('Generating %d categories for every user...' % category)
        fake_categories(category)

        click.echo('Generating %d posts for every user...' % post)
        fake_posts(post)

        click.echo('Generating %d comments for every user...' % comment)
        fake_comments(comment)

        click.echo('Generating %d corneas...' % cornea)
        fake_corneas(cornea)

        click.echo('Generating links...')
        fake_links()

        click.echo('Done.')

    @app.cli.group()
    def translate():
        """Translation and localization commands."""
        pass

    @translate.command()
    @click.argument('locale')
    def init(locale):
        """Initialize a new language."""
        if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
            raise RuntimeError('extract command failed')
        if os.system(
                'pybabel init -i messages.pot -d corneakeeper/translations -l ' + locale):
            raise RuntimeError('init command failed')
        os.remove('messages.pot')

    @translate.command()
    def update():
        """Update all languages."""
        if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
            raise RuntimeError('extract command failed')
        if os.system('pybabel update -i messages.pot -d corneakeeper/translations'):
            raise RuntimeError('update command failed')
        os.remove('messages.pot')

    @translate.command()
    def compile():
        """Compile all languages."""
        if os.system('pybabel compile -d corneakeeper/translations'):
            raise RuntimeError('compile command failed')


def register_errorhandlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return render_template('errors/400.html', description=e.description), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return render_template('errors/401.html', description=e.description), 401

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html', description=e.description), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html', description=e.description), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return render_template('errors/405.html', description=e.description), 405

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return render_template('errors/413.html', description=e.description), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html', description=e.description), 500

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template('errors/400.html', description=e.description), 400
