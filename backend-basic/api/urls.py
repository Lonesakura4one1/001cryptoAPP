from django.urls import path
from . import views

urlpatterns = [
    path('status/', views.api_status, name='api_status'),
    path('profile/', views.user_profile, name='user_profile'),
]
