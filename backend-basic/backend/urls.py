from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenObtainPairView

def health_check(request):
    return JsonResponse({'status': 'healthy', 'message': 'Crypto Platform API is running'})

def api_root(request):
    return JsonResponse({
        'message': 'Crypto Platform API',
        'version': '1.0.0',
        'endpoints': {
            'health': '/health/',
            'auth': '/auth/token/',
            'api': '/api/',
        }
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('', api_root, name='api_root'),
]
