from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create UserProfile when a new User is created"""
    if created:
        try:
            UserProfile.objects.get(user=instance)
        except UserProfile.DoesNotExist:
            # Determine role based on superuser/staff status
            if instance.is_superuser:
                role = 'manager'
            elif instance.is_staff:
                role = 'user'
            else:
                role = 'user'
            
            UserProfile.objects.create(user=instance, role=role)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        # This will be created by create_user_profile signal
        pass

def _get_ip(request):
    if request is None:
        return None
    x_fwd = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_fwd:
        return x_fwd.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
 
 
# ── Đăng nhập thành công ──────────────────────────────────
@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    from login.models import UserLoginLog, ActiveSession
 
    ip = _get_ip(request)
    ua = request.META.get('HTTP_USER_AGENT', '') if request else ''
 
    # Ghi login log
    UserLoginLog.objects.create(
        user        = user,
        action      = UserLoginLog.ACTION_LOGIN,
        ip_address  = ip,
        user_agent  = ua[:500],
        session_key = request.session.session_key or '',
    )
 
    # Tạo/reset ActiveSession
    ActiveSession.objects.update_or_create(
        user=user,
        defaults=dict(
            session_key  = request.session.session_key or '',
            ip_address   = ip,
            user_agent   = ua[:500],
            current_page = '🔐 Vừa đăng nhập',
        )
    )
 
 
# ── Đăng xuất ─────────────────────────────────────────────
@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    if user is None:
        return
 
    from login.models import UserLoginLog, ActiveSession
 
    ip = _get_ip(request)
    ua = request.META.get('HTTP_USER_AGENT', '') if request else ''
 
    UserLoginLog.objects.create(
        user        = user,
        action      = UserLoginLog.ACTION_LOGOUT,
        ip_address  = ip,
        user_agent  = ua[:500],
        session_key = (request.session.session_key or '') if request else '',
    )
 
    # Xóa session active
    ActiveSession.objects.filter(user=user).delete()
 
 
# ── Đăng nhập thất bại ────────────────────────────────────
@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    from login.models import UserLoginLog
 
    ip = _get_ip(request)
    ua = request.META.get('HTTP_USER_AGENT', '') if request else ''
 
    UserLoginLog.objects.create(
        user               = None,   # chưa xác định được user
        action             = UserLoginLog.ACTION_FAILED,
        ip_address         = ip,
        user_agent         = ua[:500],
        attempted_username = credentials.get('username', '')[:150],
    )
 
