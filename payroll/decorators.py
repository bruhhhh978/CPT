from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def require_role(*allowed_roles):
    """Decorator to check if user has required role"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Allow viewer role without login
            if 'viewer' in allowed_roles and not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            
            # Require login for other roles
            if not request.user.is_authenticated:
                messages.error(request, 'Vui lòng đăng nhập để tiếp tục.')
                return redirect('login:login')
            
            # Check if user has a profile with required role
            try:
                user_role = request.user.profile.role
            except:
                messages.error(request, 'Lỗi: Hồ sơ người dùng không hợp lệ.')
                return redirect('login:login')
            
            if user_role not in allowed_roles:
                messages.error(request, 'Bạn không có quyền truy cập trang này.')
                return redirect('login:login')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator

def manager_only(view_func):
    """Decorator to restrict access to managers only"""
    return require_role('manager')(view_func)

def user_and_manager(view_func):
    """Decorator to allow both users and managers"""
    return require_role('user', 'manager')(view_func)

def any_authenticated(view_func):
    """Decorator to allow all authenticated users"""
    return require_role('manager', 'user')(view_func)

def allow_viewer(view_func):
    """Decorator to allow viewers (read-only access)"""
    return require_role('manager', 'user', 'viewer')(view_func)
