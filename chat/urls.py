from django.urls import path
from . import views
from .views import (
    login_view, register_view, logout_view, 
    session_list_view,
    chat_view, chat_api, detect_emotion,
    trend_view, trend_page_view  # ✅ 确保引入了 trend_page_view
)

urlpatterns = [
    # ✅ 用户注册与登录
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),

    # ✅ 会话列表
    path('', session_list_view, name='session_list'),

    # ✅ 聊天页面
    path('chat/<int:session_id>/', chat_view, name='chat_page'),
    path('chat/<int:session_id>/send/', chat_api, name='chat_api'),

    # ✅ 摄像头检测情绪接口
    path('detect-emotion/', detect_emotion, name='detect_emotion'),

    # ✅ 情绪趋势数据接口（返回 JSON）
    path('trend/<int:session_id>/data/', trend_view, name='trend_data'),

    # ✅ 情绪趋势图页面（渲染 trend.html）
    path('trend/<int:session_id>/page/', trend_page_view, name='trend_page'),
]
