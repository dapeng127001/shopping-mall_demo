import random

from django import http
from django.shortcuts import render
import logging
logger = logging.getLogger('django')
# Create your views here.
from django.views import View
from django_redis import get_redis_connection
from mall_project.libs.captcha.captcha import captcha


class ImageCodeView(View):
    """返回图形验证码的类视图"""

    def get(self, request, uuid):
        """生成图形验证码，保存在Redis中，返回图片"""

        # 1.调用工具类 captcha 生成图形验证码
        text, image = captcha.generate_captcha()

        # 2.链接 redis, 获取链接对象
        redis_conn = get_redis_connection('verify_code')

        # 3.利用链接对象，保存数据到redis，使用setx函数
        # redis_conn.setx('<key>', '<expire>', '<value>')
        redis_conn.setex('img_%s' % uuid, 300, text)

        # 4.返回图片
        return http.HttpResponse(image,
                                 content_type='image/jpg')


class SMSCodeView(View):
    """短信验证码"""
    def get(self, request, mobile):
        # 1.接收参数
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('image_code_id')

        # 2.参数校验
        if not all([image_code_client, uuid]):
            return http.JsonResponse({'code': 400,
                                      'errmsg': "缺少必传参数"})

        # 3.创建连接到redis的对象
        redis_conn = get_redis_connection('verify_code')

        # 4.提取图形验证码
        image_code_server = redis_conn.get('img_%s' % uuid)
        if image_code_server is None:
            # 图形验证码过期或者不存在
            return http.JsonResponse({'code': 400,
                                      'errmsg': "图形验证码失效"})

        # 5.删除图形验证码，避免恶意测试图形验证码
        try:
            redis_conn.delete('img_%s' % uuid)
        except Exception as e:
            logger.error(e)  # 异常输入到日志文件

        # 6.对比图形验证码
        # bytes 转字符串
        image_code_server = image_code_server.decode()
        # 转小写后比较
        if image_code_client.lower() != image_code_server.lower():
            return http.JsonResponse({'code': 400,
                                      'errmsg': '输入图形验证码有误'})

        # 7.生成短信验证码：生成6位数验证码
        sms_code = '%06d' % random.randint(0, 999999)
        print(sms_code)

        # 8.保存短信验证码
        # 短信验证码有效期，单位：300秒
        redis_conn.setex('sms_%s' % mobile,
                         300,
                         sms_code)

        # 9. 发送短信验证码
        # 短信模板
        # CCP().send_template_sms(mobile, [sms_code, 5], 1)

        # 10.响应结果
        return http.JsonResponse({'code': 0,
                                  'errmsg': '发送短信成功'})
