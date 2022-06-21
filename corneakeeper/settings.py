'''
    :author: Linyi Qian (钱霖奕)
    :copyright: © 2022 Linyi Qian <qianlinyi@hhu.edu.cn>
    :license: MIT, see LICENSE for more details.
'''

import os

from flask_whooshee import AbstractWhoosheer

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Operations:
    CONFIRM = 'confirm'
    RESET_PASSWORD = 'reset-password'
    CHANGE_EMAIL = 'change-email'


class BaseConfig(object):
    SECRET_KEY = os.getenv('SECRET_KEY', 'secret_string')

    # 邮件设置
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = ('wangzai', MAIL_USERNAME)
    CK_ADMIN_EMAIL = 'qianlinyi@hhu.edu.cn'
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    # BLOG_EMAIL = os.getenv('BLUELOG_EMAIL')
    BLOG_POST_PER_PAGE = 10
    BLOG_MANAGE_POST_PER_PAGE = 15
    BLOG_COMMENT_PER_PAGE = 15
    MW_THEMES = {'perfect_blue': 'Perfect Blue', 'black_swan': 'Black Swan'}

    #  设置语言
    MW_LANGUAGE = {'cn': 'Chinese', 'en': 'English'}

    BLUELOG_SLOW_QUERY_THRESHOLD = 1

    #  BLUELOG_UPLOAD_PATH = os.path.join(basedir, 'uploads')
    BLUELOG_ALLOWED_IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif']

    #  图片展示设置
    CK_PHOTO_PER_PAGE = 12
    CK_USER_PER_PAGE = 20

    #  图片上传设置
    CK_UPLOAD_PATH = os.path.join(basedir, 'uploads')  # 图片上传路径
    CK_PHOTO_SIZE = {'small': 400, 'medium': 800}  # 图片大小
    CK_PHOTO_SUFFIX = {
        CK_PHOTO_SIZE['small']: '_s',  # thumbnail
        CK_PHOTO_SIZE['medium']: '_m',  # display
    }  # 图片后缀

    # DROPZONE 配置
    DROPZONE_MAX_FILE_SIZE = 3
    DROPZONE_MAX_FILES = 30
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024
    DROPZONE_ALLOWED_FILE_TYPE = 'image'
    DROPZONE_DEFAULT_MESSAGE = u'拖拽文件到这里或点击上传<br>Drop files here or click to upload.'
    DROPZONE_ENABLE_CSRF = True
    # 头像
    AVATARS_SAVE_PATH = os.path.join(CK_UPLOAD_PATH, 'avatars')  # 头像存储路径
    AVATARS_SIZE_TUPLE = (30, 100, 200)  # 头像大小

    # 搜索
    SEARCH_RESULT_PER_PAGE = 10
    WHOOSHEE_MIN_STRING_LEN = 1
    AbstractWhoosheer.auto_update = False

    BOOTSTRAP_BTN_STYLE = 'light'

    # 富文本编辑器
    CKEDITOR_HEIGHT = 800

    # 区域代码
    CK_LOCALES = ['zh', 'en']
    BABEL_DEFAULT_LOCALE = CK_LOCALES[0]  # 默认区域

    # 数据库设置
    USERNAME = os.getenv('MYSQL_USERNAME')
    PASSWORD = os.getenv('MYSQL_PASSWORD')
    IP = os.getenv('MYSQL_IP')
    HOST = os.getenv('MYSQL_HOST')
    DATABASE = os.getenv('DATABASE')


class DevelopmentConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = 'mysql://{}:{}@{}:{}/{}'.format(BaseConfig.USERNAME, BaseConfig.PASSWORD, BaseConfig.IP, BaseConfig.HOST, BaseConfig.DATABASE)


class TestingConfig(DevelopmentConfig):
    pass


class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://{}:{}@{}:{}/{}'.format(BaseConfig.USERNAME, BaseConfig.PASSWORD, BaseConfig.IP, BaseConfig.HOST, BaseConfig.DATABASE)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}
