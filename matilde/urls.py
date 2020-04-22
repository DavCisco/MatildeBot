from django.contrib import admin
from django.urls import path, include

from bot import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('events/', views.webhook, name='webhook'),
]
