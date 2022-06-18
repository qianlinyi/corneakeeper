from datetime import datetime
from flask import current_app
from flask_login import UserMixin
from flask_avatars import Identicon
from corneakeeper.extensions import db, whooshee
from werkzeug.security import generate_password_hash, check_password_hash

# relationship table
roles_permissions = db.Table('roles_permissions',
                             db.Column('role_id', db.Integer,
                                       db.ForeignKey('role.id')),
                             db.Column('permission_id', db.Integer,
                                       db.ForeignKey('permission.id'))
                             )


class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    roles = db.relationship('Role', secondary=roles_permissions,
                            back_populates='permissions')


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    users = db.relationship('User', back_populates='role')
    permissions = db.relationship('Permission', secondary=roles_permissions,
                                  back_populates='roles')

    @staticmethod
    def init_role():
        roles_permissions_map = {
            'Limited': ['USER_MANAGE'],
            'User': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD', 'CREATE',
                     'MANAGE'],
            'Admin': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD', 'CREATE',
                      'MANAGE', 'ADMINISTER']
        }

        for role_name in roles_permissions_map:
            role = Role.query.filter_by(name=role_name).first()
            if role is None:
                role = Role(name=role_name)
                db.session.add(role)
            role.permissions = []
            for permission_name in roles_permissions_map[role_name]:
                permission = Permission.query.filter_by(
                    name=permission_name).first()
                if permission is None:
                    permission = Permission(name=permission_name)
                    db.session.add(permission)
                role.permissions.append(permission)
        db.session.commit()


# relationship object
class Follow(db.Model):
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    follower = db.relationship('User', foreign_keys=[follower_id],
                               back_populates='following', lazy='joined')
    followed = db.relationship('User', foreign_keys=[followed_id],
                               back_populates='followers', lazy='joined')


@whooshee.register_model('username', 'name')
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20))
    password_hash = db.Column(db.String(128))

    blog_title = db.Column(db.String(60))
    blog_sub_title = db.Column(db.String(100))
    name = db.Column(db.String(30))
    about = db.Column(db.Text)
    email = db.Column(db.String(254), unique=True, index=True)
    website = db.Column(db.String(255))
    bio = db.Column(db.String(120))
    location = db.Column(db.String(50))
    member_since = db.Column(db.DateTime, default=datetime.utcnow)
    locale = db.Column(db.String(20))  # 区域

    # 隐私设置
    public_charts = db.Column(db.Boolean, default=False)  # 变化隐私
    public_diagnosis = db.Column(db.Boolean, default=False)  # 诊断隐私
    public_photos = db.Column(db.Boolean, default=False)  # 图片隐私
    public_collections = db.Column(db.Boolean, default=False)  # 收藏隐私
    public_followings = db.Column(db.Boolean, default=False)  # 关注隐私
    public_followers = db.Column(db.Boolean, default=False)  # 粉丝隐私

    receive_comment_notification = db.Column(db.Boolean, default=True)
    receive_follow_notification = db.Column(db.Boolean, default=True)
    receive_collect_notification = db.Column(db.Boolean, default=True)

    # 用户状态
    confirmed = db.Column(db.Boolean, default=False)
    locked = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)

    # 头像尺寸
    avatar_s = db.Column(db.String(64))
    avatar_m = db.Column(db.String(64))
    avatar_l = db.Column(db.String(64))
    avatar_raw = db.Column(db.String(64))

    cornea = db.relationship('Cornea',
                             back_populates='user')  # 与 cornea 建立一对多关系
    comments = db.relationship('Comment', back_populates='user',
                               cascade='all')  # 建立用户和评论的一对多关系
    role_id = db.Column(db.Integer,
                        db.ForeignKey('role.id'))  # 存储 Role 记录主键值的外键字段
    role = db.relationship('Role', back_populates='users')  # 建立角色和用户的一对多关系
    posts = db.relationship('Post', back_populates='user')  # 建立用户和文章的一对多关系
    photos = db.relationship('Photo', back_populates='user',
                             cascade='all')  # 用户和图片建立一对多关系
    notifications = db.relationship('Notification', back_populates='receiver',
                                    cascade='all')  # 建立用户和通知的一对多关系
    photo_collections = db.relationship('CollectPhoto',
                                        back_populates='collector',
                                        lazy='joined')
    post_collections = db.relationship('CollectPost',
                                       back_populates='collector',
                                       lazy='joined')
    following = db.relationship('Follow', foreign_keys=[Follow.follower_id],
                                back_populates='follower',
                                lazy='dynamic', cascade='all')
    followers = db.relationship('Follow', foreign_keys=[Follow.followed_id],
                                back_populates='followed',
                                lazy='dynamic', cascade='all')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        self.generate_avatar()  # 生成用户头像
        # self.follow(self)  # follow self, 不用自己跟自己
        self.set_role()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_role(self):
        if self.role is None:
            if self.email == current_app.config['CK_ADMIN_EMAIL']:
                self.role = Role.query.filter_by(name='Admin').first()
            else:
                self.role = Role.query.filter_by(name='User').first()
            db.session.commit()

    @property
    def is_admin(self):
        return self.role.name == 'Admin'

    def collect_post(self, post):
        if not self.is_collecting_post(post):
            collect = CollectPost(collector=self, collected=post)
            db.session.add(collect)
            db.session.commit()

    def uncollect_post(self, post):
        collect = CollectPost.query.with_parent(self).filter_by(
            collected_id=post.id).first()
        if collect:
            db.session.delete(collect)
            db.session.commit()

    def is_collecting_post(self, post):
        return CollectPost.query.with_parent(self).filter_by(
            collected_id=post.id).first() is not None

    def collect_photo(self, photo):
        if not self.is_collecting_photo(photo):
            collect = CollectPhoto(collector=self, collected=photo)
            db.session.add(collect)
            db.session.commit()

    def uncollect_photo(self, photo):
        collect = CollectPhoto.query.with_parent(self).filter_by(
            collected_id=photo.id).first()
        if collect:
            db.session.delete(collect)
            db.session.commit()

    def is_collecting_photo(self, photo):
        return CollectPhoto.query.with_parent(self).filter_by(
            collected_id=photo.id).first() is not None

    def follow(self, user):
        if not self.is_following(user):
            follow = Follow(follower=self, followed=user)
            db.session.add(follow)
            db.session.commit()

    def unfollow(self, user):
        follow = self.following.filter_by(followed_id=user.id).first()
        if follow:
            db.session.delete(follow)
            db.session.commit()

    def is_following(self, user):
        if user.id is None:  # when follow self, user.id will be None
            return False
        return self.following.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

    # 验证当前用户权限
    def can(self, permission_name):
        permission = Permission.query.filter_by(name=permission_name).first()
        return permission is not None and self.role is not None and permission in self.role.permissions

    # 生成头像文件
    def generate_avatar(self):
        avatar = Identicon()
        filenames = avatar.generate(text=self.username)
        self.avatar_s = filenames[0]
        self.avatar_m = filenames[1]
        self.avatar_l = filenames[2]
        db.session.commit()


tagging = db.Table('tagging',
                   db.Column('photo_id', db.Integer, db.ForeignKey('photo.id')),
                   db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
                   )


# 建立用户和文章模型的多对多关系
class CollectPost(db.Model):
    collector_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                             primary_key=True)
    collected_id = db.Column(db.Integer, db.ForeignKey('post.id'),
                             primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())
    collector = db.relationship('User', back_populates='post_collections',
                                lazy='joined')
    collected = db.relationship('Post', back_populates='collectors',
                                lazy='joined')


# 建立用户和照片模型的多对多关系
class CollectPhoto(db.Model):
    collector_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                             primary_key=True)
    collected_id = db.Column(db.Integer, db.ForeignKey('photo.id'),
                             primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # 通过 CollectPhoto 模型建立 User 和 Photo 的多对多关系
    collector = db.relationship('User', back_populates='photo_collections',
                                lazy='joined')
    collected = db.relationship('Photo', back_populates='collectors',
                                lazy='joined')


@whooshee.register_model('description')
class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500))
    filename = db.Column(db.String(64))
    filename_s = db.Column(db.String(64))
    filename_m = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    can_comment = db.Column(db.Boolean, default=True)  # 是否可以评论

    # 建立用户和照片的一对多关系
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='photos')

    collectors = db.relationship('CollectPhoto', back_populates='collected',
                                 lazy='joined')
    tags = db.relationship('Tag', secondary=tagging, back_populates='photos')
    comments = db.relationship('Comment', back_populates='photo',
                               cascade='all')  # 建立图片和 comment 的一对多关系


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)

    # 建立分类和文章的一对多关系
    posts = db.relationship('Post', back_populates='category')

    # #  建立用户和分类的一对多关系
    # user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # user = db.relationship('User', back_populates='posts')
    def delete(self):
        default_category = Category.query.get(1)
        posts = self.posts[:]
        for post in posts:
            post.category = default_category
        db.session.delete(self)
        db.session.commit()


@whooshee.register_model('title', 'body')
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    can_comment = db.Column(db.Boolean, default=True)

    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))

    #  建立用户和文章的一对多关系
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='posts')
    collectors = db.relationship('CollectPost', back_populates='collected',
                                 lazy='joined')
    category = db.relationship('Category', back_populates='posts')
    comments = db.relationship('Comment', back_populates='post',
                               cascade='all, delete-orphan')


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(30))
    email = db.Column(db.String(254))
    site = db.Column(db.String(255))
    body = db.Column(db.Text)
    from_admin = db.Column(db.Boolean, default=False)
    reviewed = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    replied_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    replies = db.relationship('Comment', back_populates='replied',
                              cascade='all, delete-orphan')
    replied = db.relationship('Comment', back_populates='replies',
                              remote_side=[id])

    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))  # 建立文章和评论的一对多关系
    post = db.relationship('Post', back_populates='comments')

    photo_id = db.Column(db.Integer, db.ForeignKey('photo.id'))
    photo = db.relationship('Photo', back_populates='comments')  # 建立图片和评论的一对多关系

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='comments')  # 建立用户和评论的一对多关系


class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30))
    url = db.Column(db.String(255))


class Cornea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    k1 = db.Column(db.Float)
    k2 = db.Column(db.Float)
    k_max = db.Column(db.Float)
    thickness_min = db.Column(db.Integer)
    datetime = db.Column(db.DateTime)
    updatetime = db.Column(db.DateTime)
    BSCVA = db.Column(db.DECIMAL(2, 1))
    UCVA = db.Column(db.DECIMAL(2, 1))
    myopia = db.Column(db.Integer)
    astigmatism = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 定义外键
    user = db.relationship('User', back_populates='cornea')  # 与 User 建立一对多关系


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver = db.relationship('User',
                               back_populates='notifications')  # 与 user 建立一对多关系


@whooshee.register_model('name')
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    photos = db.relationship('Photo', secondary=tagging, back_populates='tags')
