from django.apps import AppConfig


class ComplianceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.compliance'
    verbose_name = 'Compliance & KYC'
    
    def ready(self):
        # Import signal handlers
        from . import signals
