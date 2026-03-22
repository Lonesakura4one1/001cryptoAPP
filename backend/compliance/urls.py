from django.urls import path
from . import views

urlpatterns = [
    # User KYC endpoints
    path('kyc/profile/', views.submit_kyc_profile, name='submit_kyc_profile'),
    path('kyc/document/', views.upload_kyc_document, name='upload_kyc_document'),
    path('kyc/status/', views.get_kyc_status, name='get_kyc_status'),
    
    # Compliance alerts
    path('alerts/', views.get_compliance_alerts, name='get_compliance_alerts'),
    path('alerts/<int:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
    
    # Transaction compliance
    path('check-transaction/', views.check_transaction_compliance, name='check_transaction_compliance'),
    
    # Admin endpoints
    path('admin/kyc/pending/', views.get_pending_kyc_reviews, name='get_pending_kyc_reviews'),
    path('admin/kyc/<int:document_id>/approve/', views.approve_kyc_document, name='approve_kyc_document'),
    path('admin/kyc/<int:document_id>/reject/', views.reject_kyc_document, name='reject_kyc_document'),
]
