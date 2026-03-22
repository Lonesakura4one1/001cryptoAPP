from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

@api_view(['GET'])
def api_status(request):
    return Response({
        'status': 'success',
        'message': 'Crypto Platform API is working',
        'services': {
            'authentication': 'JWT',
            'database': 'SQLite',
            'framework': 'Django REST Framework'
        }
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
def user_profile(request):
    if request.user.is_authenticated:
        return Response({
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
            }
        })
    else:
        return Response({
            'error': 'Authentication required'
        }, status=status.HTTP_401_UNAUTHORIZED)
