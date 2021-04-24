from django.urls import re_path

from users import views

urlpatterns = [
    # 判断用户名是否重复
    re_path(r'^usernames/(?P<username>\w{5,20})/count/$', views.UsernameCountView.as_view()),
    # 判断手机号是否重复
    re_path(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MobileCountView.as_view()),
    # 注册
    re_path(r'^register/$', views.RegisterView.as_view()),
    # 登录
    re_path(r'^login/$', views.LoginView.as_view()),
    # 退出登录
    re_path(r'^logout/$', views.LogoutView.as_view()),
    # 用户中心
    re_path(r'^info/$', views.UserInfoView.as_view()),
    # 新增收货地址
    re_path(r'^addresses/create/$', views.CreateAddressView.as_view()),
]
