from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import KYCProfile, KYCDocument, ComplianceAlert
from .services import KYCService, AMLService, ComplianceEngine


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_kyc_profile(request):
    """Submit KYC profile for verification"""
    try:
        data = request.data
        
        # Check if profile already exists
        if hasattr(request.user, 'kyc_profile'):
            return Response({'error': 'KYC profile already exists'}, status=400)
        
        # Create KYC profile
        profile = KYCService.create_kyc_profile(request.user, data)
        
        # Log security event
        from users.models import SecurityLog
        SecurityLog.objects.create(
            user=request.user,
            event_type='kyc_submitted',
            details={
                'verification_level': profile.verification_level,
                'timestamp': timezone.now().isoformat()
            }
        )
        
        return Response({
            'message': 'KYC profile submitted successfully',
            'profile_id': profile.id,
            'verification_level': profile.verification_level
        }, status=201)
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_kyc_document(request):
    """Upload KYC document for verification"""
    try:
        data = request.data
        files = request.FILES
        
        # Validate required fields
        required_fields = ['document_type']
        for field in required_fields:
            if field not in data:
                return Response({'error': f'{field} is required'}, status=400)
        
        # Validate required files
        required_files = ['front_image']
        for file_field in required_files:
            if file_field not in files:
                return Response({'error': f'{file_field} is required'}, status=400)
        
        # Create document record
        document = KYCDocument.objects.create(
            user=request.user,
            document_type=data['document_type'],
            document_number=data.get('document_number', ''),
            expiry_date=data.get('expiry_date'),
            front_image=files['front_image'],
            back_image=files.get('back_image'),
            selfie_image=files.get('selfie_image')
        )
        
        # Update user verification level if this is first document
        if not hasattr(request.user, 'kyc_profile'):
            KYCService.create_kyc_profile(request.user, {
                'first_name': data.get('first_name', ''),
                'last_name': data.get('last_name', ''),
                'date_of_birth': data.get('date_of_birth'),
                'nationality': data.get('nationality', ''),
                'country_of_residence': data.get('country_of_residence', ''),
                'address_line_1': data.get('address_line_1', ''),
                'city': data.get('city', ''),
                'state_province': data.get('state_province', ''),
                'postal_code': data.get('postal_code', ''),
                'phone_number': data.get('phone_number', ''),
            })
        
        return Response({
            'message': 'Document uploaded successfully',
            'document_id': document.id,
            'status': document.status
        }, status=201)
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_kyc_status(request):
    """Get current KYC status"""
    try:
        profile = request.user.kyc_profile
        documents = KYCDocument.objects.filter(user=request.user)
        
        return Response({
            'verification_level': profile.verification_level,
            'verification_level_display': profile.get_verification_level_display(),
            'risk_score': profile.risk_score,
            'daily_limit': str(profile.daily_transaction_limit),
            'monthly_limit': str(profile.monthly_transaction_limit),
            'annual_limit': str(profile.annual_transaction_limit),
            'documents': [
                {
                    'id': doc.id,
                    'document_type': doc.get_document_type_display(),
                    'status': doc.get_status_display(),
                    'submitted_at': doc.created_at,
                    'verification_score': doc.verification_score
                }
                for doc in documents
            ]
        })
        
    except KYCProfile.DoesNotExist:
        return Response({
            'verification_level': 0,
            'verification_level_display': 'Not Verified',
            'risk_score': 0,
            'daily_limit': '0',
            'monthly_limit': '0',
            'annual_limit': '0',
            'documents': []
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_compliance_alerts(request):
    """Get user compliance alerts"""
    alerts = ComplianceAlert.objects.filter(user=request.user).order_by('-created_at')
    
    return Response([
        {
            'id': alert.id,
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'title': alert.title,
            'message': alert.message,
            'is_acknowledged': alert.is_acknowledged,
            'created_at': alert.created_at,
            'transaction_hash': alert.transaction_hash
        }
        for alert in alerts
    ])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def acknowledge_alert(request, alert_id):
    """Acknowledge compliance alert"""
    try:
        alert = ComplianceAlert.objects.get(id=alert_id, user=request.user)
        
        if alert.is_acknowledged:
            return Response({'error': 'Alert already acknowledged'}, status=400)
        
        alert.is_acknowledged = True
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save()
        
        return Response({'message': 'Alert acknowledged successfully'})
        
    except ComplianceAlert.DoesNotExist:
        return Response({'error': 'Alert not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_transaction_compliance(request):
    """Check transaction compliance before execution"""
    try:
        transaction_data = request.data
        
        # Run compliance evaluation
        result = ComplianceEngine.evaluate_transaction(request.user, transaction_data)
        
        return Response(result)
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


# Admin endpoints (for compliance officers)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_kyc_reviews(request):
    """Get pending KYC reviews (admin only)"""
    if not request.user.is_staff:
        return Response({'error': 'Admin access required'}, status=403)
    
    documents = KYCDocument.objects.filter(status='pending').order_by('-created_at')
    
    return Response([
        {
            'id': doc.id,
            'user_email': doc.user.email,
            'document_type': doc.get_document_type_display(),
            'submitted_at': doc.created_at,
            'verification_score': doc.verification_score
        }
        for doc in documents
    ])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_kyc_document(request, document_id):
    """Approve KYC document (admin only)"""
    if not request.user.is_staff:
        return Response({'error': 'Admin access required'}, status=403)
    
    try:
        document = KYCDocument.objects.get(id=document_id)
        document.status = 'approved'
        document.verified_by = request.user
        document.save()
        
        # Update user verification level
        KYCService.update_verification_level(document.user, 2)
        
        return Response({'message': 'Document approved successfully'})
        
    except KYCDocument.DoesNotExist:
        return Response({'error': 'Document not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_kyc_document(request, document_id):
    """Reject KYC document (admin only)"""
    if not request.user.is_staff:
        return Response({'error': 'Admin access required'}, status=403)
    
    try:
        data = request.data
        reason = data.get('reason', '')
        
        document = KYCDocument.objects.get(id=document_id)
        document.status = 'rejected'
        document.verified_by = request.user
        document.rejection_reason = reason
        document.save()
        
        return Response({'message': 'Document rejected successfully'})
        
    except KYCDocument.DoesNotExist:
        return Response({'error': 'Document not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
