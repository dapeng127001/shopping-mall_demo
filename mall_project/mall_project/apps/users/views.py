import json
import re

from django import http
from django.contrib.auth import authenticate, login, logout
from django.db import DatabaseError, transaction
from django.shortcuts import render

# Create your views here.
from django.views import View
from django_redis import get_redis_connection

from mall_project.utils.view import LoginRequiredMixin
from users.models import User, Address


class UsernameCountView(View):
    """判断用户名是否存在"""

    def get(self, request, username):
        count = User.objects.filter(username=username).count()

        return http.JsonResponse({'code': 0,
                                  'errmsg': 'OK',
                                  'count': count})


class MobileCountView(View):
    """判断手机号是否存在"""

    def get(self, request, mobile):
        count = User.objects.filter(mobile=mobile).count()

        return http.JsonResponse({'code': 0,
                                  'errmsg': 'OK',
                                  'count': count})


class RegisterView(View):
    """注册接口"""

    def post(self, request):
        # 1.接收json类型的参数
        dict = json.loads(request.body.decode())
        username = dict.get('username')
        password = dict.get('password')
        password2 = dict.get('password2')
        mobile = dict.get('mobile')
        allow = dict.get('allow')
        sms_code_client = dict.get('sms_code')

        # 2.校验参数（总体+单个）
        # 2.1总体检验，查看是否有空的参数：
        if not all([username, password, password2, mobile, sms_code_client]):
            return http.HttpResponseForbidden('缺少必传参数')

        # 2.2单个校验，查看是否能够正确匹配正则：
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('用户名为5-20位的字符串')

        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('密码为8-20位的字符串')

        if password != password2:
            return http.HttpResponseForbidden('密码不一致')

        if not re.match(r'^1[345789]\d{9}$', mobile):
            return http.HttpResponseForbidden('手机号格式不正确')

        if allow != 'true':
            return http.HttpResponseForbidden('请勾选用户协议')

        # 3.链接redis,获取链接对象
        redis_conn = get_redis_connection('verify_code')

        # 3.1从redis中取保存的短信验证码
        sms_code_server = redis_conn.get('sms_%s' % mobile)
        if sms_code_server is None:
            return http.HttpResponse(status=400)

        # 4.往mysql保存数据
        try:
            user = User.objects.create_user(username=username,
                                     password=password,
                                     mobile=mobile)
        except DatabaseError:
            # 如果出错，返回400
            return http.HttpResponse(status=400)

        # 用户信息写入到cookie
        response = http.JsonResponse({'code': 0,
                                      'errmsg': 'ok'})
        # 实现状态保持：
        login(request, user)

        # 在响应对象中设置用户名信息.
        # 将用户名写入到cookie, 有效期7天
        response.set_cookie('username',
                            user.username,
                            max_age=3600 * 24 * 7)

        # 返回响应结果
        return response


class LoginView(View):
    """登录接口"""
    def post(self, request):
        # 1.接收参数
        dict = json.loads(request.body.decode())
        username = dict.get("username")
        password = dict.get("password")
        remembered = dict.get("remembered")

        # 2.校验参数
        # 2.1整体校验
        if not all([username, password]):
            return http.HttpResponseForbidden("缺少必传参数")

        # 2.2单个校验
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden("请输入正确的用户名或手机号")

        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden("请输入正确的用户名或手机号")

        # 3.判断用户是否登录
        user = authenticate(username=username, password=password)

        if user is None:
            # 如果没有登录，返回400状态码
            return http.HttpResponse(400)

        # 4.实现状态保持
        login(request, user)

        # 5.设置状态保持的周期
        if remembered != True:
            # 不记住用户：浏览器会话结束就过期
            request.session.set_expiry(0)
        else:
            # 记住用户：None 表示两周后过期
            request.session.set_expiry(None)

        # 用户信息写入到cookie
        response = http.JsonResponse({'code': 0,
                                          'errmsg': 'ok'})

        # 在响应对象中设置用户名信息.
        # 将用户名写入到cookie, 有效期7天
        response.set_cookie('username',
                                user.username,
                                max_age=3600 * 24 * 7)

        # 返回响应结果
        return response


class LogoutView(View):
    """退出登录接口"""

    def delete(self, request):
        # 1.清理 session
        logout(request)

        # 2.创建 response 对象
        response = http.JsonResponse({'code': 0,
                                      'errmsg': 'ok'})

        # 3.调用对象的 delete_cookie 方法, 清除cookie
        response.delete_cookie('username')

        # 4.返回响应
        return response


class UserInfoView(LoginRequiredMixin, View):
    """用户中心"""
    def get(self, request):
        """提供个人信息界面"""

        # 获取界面需要的数据，进行拼接
        info_date = {
            'username': request.user.username,
            'mobile': request.user.mobile,
            'email': request.user.email,
            'email_active': request.user.email_active
        }

        # 返回响应
        return http.JsonResponse({'code': 0,
                                  'errmsg': 'ok',
                                  'info_date': info_date})





class CreateAddressView(View):
    """新增收货地址"""
    def post(self, request):
        """新增地址逻辑"""

        # 获取地址个数
        count = Address.objects.filter(user=request.user, is_deleted=False).count()

        # 判断是否超过地址上限：最多20个
        if count >= 20:
            return http.JsonResponse({'code': 400,
                                       'errmsg': '超过地址数量上限'})

        # 接收参数
        json_dict = json.loads(request.body.decode())
        