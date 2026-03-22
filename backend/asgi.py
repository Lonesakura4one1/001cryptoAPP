"""
ASGI config for backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import websocket.routing

# Use environment-based settings
env = os.environ.get('DJANGO_ENV', 'development')
if env == 'production':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings.production')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings.development')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket.routing.websocket_urlpatterns
        ),
        AllowedHostsOriginValidator(['localhost', '127.0.0.1'])
    ),
})
