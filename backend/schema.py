from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

info = openapi.Info(
    title="Crypto Trading Platform API",
    default_version='v1',
    description="Industry-standard cryptocurrency trading platform with advanced security, HD wallets, multi-signature support, and real-time trading engine",
    terms_of_service="https://example.com/terms/",
    contact=openapi.Contact(email="support@example.com"),
    license=openapi.License(name="MIT License"),
)

schema_view = get_schema_view(
    info=info,
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=[
        # Include all app URL patterns here
    ],
)
