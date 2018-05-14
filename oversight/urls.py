"""oversight URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('login/', auth_views.login, name='login'),
    path('logout/', auth_views.logout, {'next_page': '/'}, name='logout'),

    path('', views.ListBotView.as_view(), name='index'),

    # Bot urls

    path('bot/<int:pk>', views.DetailBotView.as_view(), name='bot_detail'),
    path('bot/create', views.CreateBotView.as_view(), name='bot_create'),
    path('bot/<int:pk>/edit', views.UpdateBotView.as_view(), name='bot_update'),
    path('bot/<int:pk>/delete', views.DeleteBotView.as_view(), name='bot_delete'),

    # incoming data
    path('bot/config', views.BotConfigView.as_view(), name='bot_config'),
    path('bot/report_error', views.BotErrorsView.as_view(), name='bot_report_error'),

    path('bot/<int:pk>/error/datatables', views.BotErrorsDataTablesView.as_view(), name='bot_error_datatables')
]
