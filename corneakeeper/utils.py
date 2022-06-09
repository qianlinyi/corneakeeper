try:
    from urlparse import urlparse, urljoin
except ImportError:
    from urllib.parse import urlparse, urljoin

import os
import re
import uuid
import PIL
from PIL import Image
from flask import request, redirect, url_for, current_app, flash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired
from corneakeeper.models import User
from corneakeeper.extensions import db
from corneakeeper.settings import Operations


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def redirect_back(default='blog.index', **kwargs):
    for target in request.args.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return redirect(target)
    return redirect(url_for(default, **kwargs))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['BLUELOG_ALLOWED_IMAGE_EXTENSIONS']


def generate_token(user, operation, expire_in=None, **kwargs):
    s = Serializer(current_app.config['SECRET_KEY'], expire_in)
    data = {'id': user.id, 'operation': operation}
    data.update(**kwargs)
    return s.dumps(data)


def validate_token(user, token, operation, new_password=None):
    s = Serializer(current_app.config['SECRET_KEY'])
    try:
        data = s.loads(token)
    except (SignatureExpired, BadSignature):
        return False
    if operation != data.get('operation') or user.id != data.get('id'):
        return False
    if operation == Operations.CONFIRM:
        user.confirmed = True
    elif operation == Operations.RESET_PASSWORD:
        user.set_password(new_password)
    elif operation == Operations.CHANGE_EMAIL:
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if User.query.filter_by(email=new_email).first() is not None:
            return False
        user.email = new_email
    else:
        return False
    db.session.commit()
    return True


def rename_image(old_filename):
    ext = os.path.splitext(old_filename)[1]
    new_filename = uuid.uuid4().hex + ext
    return new_filename


def resize_image(image, filename, base_width):
    filename, ext = os.path.splitext(filename)
    img = Image.open(image)
    if img.size[0] <= base_width:
        return filename + ext
    w_percent = (base_width / float(img.size[0]))
    h_size = int((float(img.size[1]) * float(w_percent)))
    img = img.resize((base_width, h_size), PIL.Image.ANTIALIAS)
    filename += current_app.config['CK_PHOTO_SUFFIX'][base_width] + ext
    img.save(os.path.join(current_app.config['CK_UPLOAD_PATH'], filename), optimize=True, quality=85)
    return filename


def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ))


def get_file_content(path):
    with open(path, 'rb') as f:
        return f.read()


def post_processing(result):
    string_text = ""  # 字符串处理
    string_list = []  # 列表处理
    for item in result['words_result']:
        str = item['words'].replace('：', ':')
        string_text += str
        word = str.split(':')
        for _ in word:
            if len(_):
                if _[-1] == 'D' and u'\u4e00' <= _[0] <= u'\u9fa5':
                    pos = 0
                    for i in range(0, len(_)):
                        if _[i].isdigit():
                            pos = i
                            break
                    string_list.append(re.sub('[(（）)\\s]', '', _[:pos]))
                    string_list.append(re.sub('[(（）)\\s]', '', _[pos:]))
                else:
                    string_list.append(re.sub('[(（）)\\s]', '', _))  # 特殊字符处理
    k1, k2, k_max, thickness_min = 0., 0., 0., 0
    # k1 判断
    if 'K1' in string_list:
        k1 = max(k1, float(re.sub('[a-zA-Z\u4e00-\u9fa5]', '',
                                  string_list[string_list.index('K1') + 1])))
    if 'k1' in string_list:
        k1 = max(k1, float(re.sub('[a-zA-Z\u4e00-\u9fa5]', '',
                                  string_list[string_list.index('k1') + 1])))
    # k2 判断
    if 'K2' in string_list:
        k2 = max(k2, float(re.sub('[a-zA-Z\u4e00-\u9fa5]', '',
                                  string_list[string_list.index('K2') + 1])))
    if 'k2' in string_list:
        k2 = max(k2, float(re.sub('[a-zA-Z\u4e00-\u9fa5]', '',
                                  string_list[string_list.index('k2') + 1])))

    # k max
    if 'KMax.Front' in string_list:
        k_max = max(k_max, float(re.sub('[a-zA-Z\u4e00-\u9fa5]', '',
                                        string_list[string_list.index('KMax.Front') + 1])))
    if 'KMaxFront' in string_list:
        k_max = max(k_max, float(re.sub('[a-zA-Z\u4e00-\u9fa5]', '',
                                        string_list[string_list.index('KMaxFront') + 1])))
    if '最大K值.前表面' in string_list:
        k_max = max(k_max, float(re.sub('[a-zA-Z\u4e00-\u9fa5]', '',
                                        string_list[string_list.index('最大K值.前表面') + 1])))
    if '最大K值前表面' in string_list:
        k_max = max(k_max, float(re.sub('[a-zA-Z\u4e00-\u9fa5]', '',
                                        string_list[string_list.index('最大K值前表面') + 1])))

    # thickness_min
    if 'ThinnestLocat' in string_list:
        thickness_min = max(thickness_min, int(re.sub('[a-zA-Z\u4e00-\u9fa5]', '',
                                                      string_list[string_list.index('ThinnestLocat') + 1])))
    if '最薄点' in string_list:
        thickness_min = max(thickness_min, int(re.sub('[a-zA-Z\u4e00-\u9fa5]', '',
                                                      string_list[string_list.index('最薄点') + 1])))
    ans = dict(
        k1=k1,
        k2=k2,
        k_max=k_max,
        thickness_min=thickness_min
    )

    return ans


#  根据不同定级给出相关治疗意见
def treat(stage):
    if stage == '正常':
        treatment = '您的眼睛很健康，请爱护好自己的眼睛！'
    elif stage == '潜伏期':
        treatment = '佩戴框架眼睛矫正视力，定期去眼科医院复查'
    elif stage == '初发期' or stage == '完成期 1 级':
        treatment = '佩戴框架眼睛或角膜塑形镜矫正视力，可根据发展情况和医生建议决定是否采取角膜胶原交联手术'
    elif stage == '完成期 2 级' or stage == '完成期 3 级':
        treatment = '佩戴框架眼睛或角膜塑形镜矫正视力，可根据发展情况和医生建议决定是否采取角膜移植手术'
    elif stage == 'Normal':
        treatment = 'Your eyes are healthy, please insist on your eye-protection!'
    elif stage == 'Early Keratoconus (Stage 1)':
        treatment = 'Early stage keratoconus is treated by using spectacles or contact lenses. Spectacles help in ' \
                    'fixing myopia and astigmatism and provide adequate vision to the patient. Soft contact lenses ' \
                    'containing spherical or toric corrections are considered as the best option while performing ' \
                    'sport activities. '
    elif stage == 'Moderate Keratoconus (Stage 2)':
        treatment = 'Rigid gas permeable contact lenses are considered as the most suitable option for moderate ' \
                    'keratoconus patients, as it provides better quality vision than spectacles. These lenses are ' \
                    'accessible in different diameters ranging from 8.0 - 20.0 mm in a miniscleral form.They cover ' \
                    'the entire corneal irregularity using a regular hard surface and neutralize about 90% of the ' \
                    'corneal distortion in your eye. The focusing power of the contact lens is helpful in reducing ' \
                    'the effect of myopia, hyperopia and astigmatism in the patient. This further provides a better ' \
                    'contrast, reduces ghosting and flaring and offers a much clearer vision.Hybrid lenses are those ' \
                    'rigid gas permeable lenses which are surrounded with a soft material. They provide excellent ' \
                    'vision quality with great comfort and stability. A new form of soft lens called KeraSoft, ' \
                    'is also effective for moderate keratoconus cases.Emergency spectacles can be used as a back-up, ' \
                    'if you experience eye irritation or if your lenses get lost. These spectacles do not provide ' \
                    '100% clarity to your vision, but can be used as an alternative in some situations.It is very ' \
                    'important to undergo regular reviews of your eyes to check progression of the keratoconus. The ' \
                    'doctor will check your eye condition and fitting of the rigid gas permeable contact lenses. ' \
                    'This helps your doctor ensure stability of the vision and maintain a healthy eye. '
    elif stage == 'Advanced Keratoconus (Stage 3)':
        treatment = 'Specialized rigid gas permeable contact lens design is used for the treatment of advanced stage ' \
                    'keratoconus. They involve greater changes in their design by considering a much steeper inner ' \
                    'curvature to maintain an appropriate fitting of the lens. Large miniscleral or scleral rigid ' \
                    'gas permeable contact lenses are beneficial for people having an unusually shaped cornea. They ' \
                    'vault cornea and improve stability and comfort in eyes. '
    else:
        treatment = 'Severe keratoconus patients require a corneal transplant surgery as spectacles and specialized ' \
                    'lenses are not suitable for their treatment. You can refer to an experienced corneal surgeon ' \
                    'for a corneal transplant. '
    return treatment


#  删除文件夹下的所有文件
def del_files(path):
    ls = os.listdir(path)
    for i in ls:
        f_path = os.path.join(path, i)
        # 判断是否是一个目录,若是,则递归删除
        if os.path.isdir(f_path):
            del_files(f_path)
        else:
            os.remove(f_path)
