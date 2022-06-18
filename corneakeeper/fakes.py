import random

from faker import Faker
from sqlalchemy.exc import IntegrityError

from corneakeeper.extensions import db
from corneakeeper.models import User, Category, Post, Comment, Link, Cornea

fake = Faker('zh-CN')


# 生成虚拟管理员信息
def fake_admin():
    admin = User(
        username='admin',
        blog_title='Cornea Keeper',
        blog_sub_title="No, I'm the real thing.",
        name='Mima Kirigoe',
        email='qianlinyi@hhu.edu.cn',
        website='example.com',
        about='Um, l, Mima Kirigoe, had a fun time as a member of CHAM...'
    )
    admin.set_password('helloflask')
    db.session.add(admin)
    db.session.commit()


# 生成虚拟用户信息
def fake_user(count=10):
    for i in range(count):
        user = User(
            name=fake.name(),
            confirmed=True,
            username=fake.user_name(),
            email=fake.email(),
            website=fake.url()
        )
        user.set_password('12345678')
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


def fake_categories(count=10):
    category = Category(name='Default')
    db.session.add(category)

    for i in range(count):
        category = Category(name=fake.word())
        db.session.add(category)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


def fake_posts(count=5):
    for i in range(User.query.count()):
        for j in range(count):
            post = Post(
                title=fake.sentence(),
                body=fake.text(2000),
                category=Category.query.get(random.randint(1, Category.query.count())),
                timestamp=fake.date_time_this_year(),
                user=User.query.get(i + 1)
            )
            db.session.add(post)
        db.session.commit()


def fake_comments(count=20):
    # 设置每个用户发的评论(已查看)
    for i in range(User.query.count()):
        for j in range(count):
            comment = Comment(
                author=User.query.get(i + 1).name,
                email=User.query.get(i + 1).email,
                site=User.query.get(i + 1).website,
                body=fake.sentence(),
                timestamp=fake.date_time_this_year(),
                reviewed=True,
                post=Post.query.get(random.randint(1, Post.query.count())),
                user=User.query.get(i + 1)
            )
            db.session.add(comment)

    # 设置每个用户发的评论(未查看)
    for i in range(User.query.count()):
        for j in range(count):
            comment = Comment(
                author=User.query.get(i + 1).name,
                email=User.query.get(i + 1).email,
                site=User.query.get(i + 1).website,
                body=fake.sentence(),
                timestamp=fake.date_time_this_year(),
                reviewed=False,
                post=Post.query.get(random.randint(1, Post.query.count())),
                user=User.query.get(i + 1)
            )
            db.session.add(comment)

    for i in range(count * 10):
        # from admin
        comment = Comment(
            author='Mima Kirigoe',
            email='qianlinyi@hhu.edu.cn',
            site='example.com',
            body=fake.sentence(),
            timestamp=fake.date_time_this_year(),
            from_admin=True,
            reviewed=True,
            post=Post.query.get(random.randint(1, Post.query.count())),
            user=User.query.get(1)
        )
        db.session.add(comment)
    db.session.commit()

    # for i in range(User.query.count()):
    #     # replies
    #     for j in range(count):
    #         comment = Comment(
    #             author=fake.name(),
    #             email=fake.email(),
    #             site=fake.url(),
    #             body=fake.sentence(),
    #             timestamp=fake.date_time_this_year(),
    #             reviewed=True,
    #             replied=Comment.query.get(random.randint(1, Comment.query.count())),
    #             post=Post.query.get(random.randint(1, Post.query.count())),
    #             user=User.query.get(i + 1)
    #         )
    #         db.session.add(comment)
    #     db.session.commit()


def fake_links():
    twitter = Link(name='Twitter', url='#')
    facebook = Link(name='Facebook', url='#')
    linkedin = Link(name='LinkedIn', url='#')
    google = Link(name='Google+', url='#')
    db.session.add_all([twitter, facebook, linkedin, google])
    db.session.commit()


def fake_corneas(count=10):
    for i in range(User.query.count()):
        for j in range(count):
            cornea = Cornea(
                k1=round(random.uniform(30, 80), 1),
                k2=round(random.uniform(30, 80), 1),
                k_max=round(random.uniform(50, 80), 1),
                thickness_min=random.randint(200, 600),
                datetime=fake.date_time_this_year(),
                updatetime=fake.date_time_this_year(),
                user=User.query.get(i + 1),
                BSCVA=round(random.uniform(0, 1.5), 1),
                UCVA=round(random.uniform(0, 1.5), 1),
                myopia=random.randint(0, 2000),
                astigmatism=random.randint(0, 2000)
            )
            db.session.add(cornea)
        db.session.commit()
