"""
Health check views for crypto platform.
"""

import psutil
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.core.cache import cache
from django.utils import timezone
import redis
import os


@require_GET
def health_check(request):
    """
    Comprehensive health check endpoint.
    Returns overall system health status.
    """
    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0',
        'checks': {}
    }
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['checks']['database'] = {
            'status': 'healthy',
            'message': 'Database connection successful'
        }
    except Exception as e:
        health_status['checks']['database'] = {
            'status': 'unhealthy',
            'message': str(e)
        }
        health_status['status'] = 'unhealthy'
    
    # Redis check
    try:
        redis_client = redis.from_url(settings.CACHES['default']['LOCATION'])
        redis_client.ping()
        health_status['checks']['redis'] = {
            'status': 'healthy',
            'message': 'Redis connection successful'
        }
    except Exception as e:
        health_status['checks']['redis'] = {
            'status': 'unhealthy',
            'message': str(e)
        }
        health_status['status'] = 'unhealthy'
    
    # Cache check
    try:
        cache.set('health_check', 'ok', 10)
        cache_result = cache.get('health_check')
        if cache_result == 'ok':
            health_status['checks']['cache'] = {
                'status': 'healthy',
                'message': 'Cache read/write successful'
            }
        else:
            raise Exception('Cache read/write failed')
    except Exception as e:
        health_status['checks']['cache'] = {
            'status': 'unhealthy',
            'message': str(e)
        }
        health_status['status'] = 'unhealthy'
    
    # Disk space check
    try:
        disk_usage = psutil.disk_usage('/')
        disk_percent = (disk_usage.used / disk_usage.total) * 100
        
        threshold = getattr(settings, 'HEALTH_CHECK', {}).get('DISK_USAGE_MAX', 90)
        
        if disk_percent < threshold:
            health_status['checks']['disk'] = {
                'status': 'healthy',
                'message': f'Disk usage: {disk_percent:.1f}%'
            }
        else:
            health_status['checks']['disk'] = {
                'status': 'warning',
                'message': f'Disk usage high: {disk_percent:.1f}%'
            }
            if health_status['status'] == 'healthy':
                health_status['status'] = 'warning'
    except Exception as e:
        health_status['checks']['disk'] = {
            'status': 'unhealthy',
            'message': str(e)
        }
        health_status['status'] = 'unhealthy'
    
    # Memory check
    try:
        memory = psutil.virtual_memory()
        memory_mb = memory.available / (1024 * 1024)
        threshold = getattr(settings, 'HEALTH_CHECK', {}).get('MEMORY_MIN', 100)
        
        if memory_mb > threshold:
            health_status['checks']['memory'] = {
                'status': 'healthy',
                'message': f'Available memory: {memory_mb:.1f}MB'
            }
        else:
            health_status['checks']['memory'] = {
                'status': 'warning',
                'message': f'Low memory: {memory_mb:.1f}MB'
            }
            if health_status['status'] == 'healthy':
                health_status['status'] = 'warning'
    except Exception as e:
        health_status['checks']['memory'] = {
            'status': 'unhealthy',
            'message': str(e)
        }
        health_status['status'] = 'unhealthy'
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)


@require_GET
def readiness_check(request):
    """
    Readiness probe - checks if application is ready to serve traffic.
    """
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check Redis connection
        redis_client = redis.from_url(settings.CACHES['default']['LOCATION'])
        redis_client.ping()
        
        return JsonResponse({
            'status': 'ready',
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'status': 'not_ready',
            'timestamp': timezone.now().isoformat(),
            'error': str(e)
        }, status=503)


@require_GET
def liveness_check(request):
    """
    Liveness probe - checks if application is alive.
    """
    return JsonResponse({
        'status': 'alive',
        'timestamp': timezone.now().isoformat(),
        'uptime': psutil.boot_time()
    })


@require_GET
def metrics_check(request):
    """
    Basic metrics endpoint.
    """
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Django metrics
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM auth_user")
            user_count = cursor.fetchone()[0]
        
        metrics = {
            'timestamp': timezone.now().isoformat(),
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available / (1024 * 1024),
                'disk_percent': (disk.used / disk.total) * 100,
                'disk_free_gb': disk.free / (1024 * 1024 * 1024)
            },
            'application': {
                'user_count': user_count,
                'debug_mode': settings.DEBUG,
                'environment': os.environ.get('DJANGO_ENV', 'development')
            }
        }
        
        return JsonResponse(metrics)
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)
