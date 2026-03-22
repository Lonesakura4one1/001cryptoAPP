from django.utils import timezone
from .models import SecurityLog, UserSession


class SecurityMiddleware:
    """Security middleware for logging and session management"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get client IP
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Log security events
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Update user session
            self.update_user_session(request, ip_address, user_agent)
            
            # Log login if this is a new session
            if not request.session.get('login_logged'):
                SecurityLog.objects.create(
                    user=request.user,
                    event_type='login_success',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={'timestamp': timezone.now().isoformat()}
                )
                request.session['login_logged'] = True
        
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def update_user_session(self, request, ip_address, user_agent):
        """Update or create user session"""
        session_key = request.session.session_key
        
        UserSession.objects.update_or_create(
            user=request.user,
            session_key=session_key,
            defaults={
                'ip_address': ip_address,
                'user_agent': user_agent,
                'is_active': True,
                'last_activity': timezone.now()
            }
        )
