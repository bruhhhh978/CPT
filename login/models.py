from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('manager', 'Cấp 1 - Quản lý'),
        ('user', 'Cấp 2 - Người dùng'),
        ('viewer', 'Cấp 3 - Người xem'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user', verbose_name='Cấp độ')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    class Meta:
        verbose_name = "Hồ sơ người dùng"
        verbose_name_plural = "Hồ sơ người dùng"

# ── 1. Lịch sử đăng nhập ───────────────────────────────────
class UserLoginLog(models.Model):
    ACTION_LOGIN  = 'LOGIN'
    ACTION_LOGOUT = 'LOGOUT'
    ACTION_FAILED = 'FAILED'
    ACTION_CHOICES = [
        (ACTION_LOGIN,  'Đăng nhập'),
        (ACTION_LOGOUT, 'Đăng xuất'),
        (ACTION_FAILED, 'Đăng nhập thất bại'),
    ]
 
    user               = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='login_logs', null=True, blank=True,
                             verbose_name='Người dùng')
    action             = models.CharField(max_length=10, choices=ACTION_CHOICES,
                             default=ACTION_LOGIN, verbose_name='Hành động')
    ip_address         = models.GenericIPAddressField(null=True, blank=True,
                             verbose_name='Địa chỉ IP')
    user_agent         = models.TextField(blank=True, verbose_name='Trình duyệt / Thiết bị')
    session_key        = models.CharField(max_length=40, blank=True,
                             verbose_name='Session key')
    attempted_username = models.CharField(max_length=150, blank=True,
                             verbose_name='Username (khi thất bại)')
    created_at         = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian')
 
    class Meta:
        db_table             = 'user_login_log'
        ordering             = ['-created_at']
        verbose_name         = 'Lịch sử đăng nhập'
        verbose_name_plural  = 'Lịch sử đăng nhập'
        indexes = [
            models.Index(fields=['user', '-created_at'], name='login_log_user_time_idx'),
            models.Index(fields=['-created_at'],          name='login_log_time_idx'),
            models.Index(fields=['action'],               name='login_log_action_idx'),
        ]
 
    def __str__(self):
        who = self.user.username if self.user else self.attempted_username
        return f"{who} — {self.get_action_display()} @ {self.created_at:%d/%m/%Y %H:%M}"
 
    @property
    def browser_short(self):
        """Trả về tên trình duyệt ngắn gọn từ User-Agent."""
        ua = self.user_agent.lower()
        if 'edg' in ua:    return 'Edge'
        if 'chrome' in ua: return 'Chrome'
        if 'firefox' in ua:return 'Firefox'
        if 'safari' in ua: return 'Safari'
        if 'opera' in ua:  return 'Opera'
        return 'Khác'
 
 
# ── 2. Nhật ký hoạt động ───────────────────────────────────
class UserActivityLog(models.Model):
    ACTION_VIEW   = 'VIEW'
    ACTION_CREATE = 'CREATE'
    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'
    ACTION_EXPORT = 'EXPORT'
    ACTION_IMPORT = 'IMPORT'
    ACTION_LOGIN  = 'LOGIN'
    ACTION_CHOICES = [
        (ACTION_VIEW,   'Xem'),
        (ACTION_CREATE, 'Tạo mới'),
        (ACTION_UPDATE, 'Chỉnh sửa'),
        (ACTION_DELETE, 'Xóa'),
        (ACTION_EXPORT, 'Xuất file'),
        (ACTION_IMPORT, 'Nhập file'),
        (ACTION_LOGIN,  'Đăng nhập'),
    ]
 
    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                     related_name='activity_logs', verbose_name='Người dùng')
    action_type = models.CharField(max_length=10, choices=ACTION_CHOICES,
                     verbose_name='Loại hành động')
    model_name  = models.CharField(max_length=50, blank=True, verbose_name='Đối tượng')
    object_id   = models.CharField(max_length=50, blank=True, verbose_name='ID')
    object_repr = models.CharField(max_length=200, blank=True, verbose_name='Tên đối tượng')
    path        = models.CharField(max_length=500, blank=True, verbose_name='URL')
    description = models.TextField(blank=True, verbose_name='Mô tả chi tiết')
    ip_address  = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP')
    created_at  = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian')
 
    class Meta:
        db_table             = 'user_activity_log'
        ordering             = ['-created_at']
        verbose_name         = 'Nhật ký hoạt động'
        verbose_name_plural  = 'Nhật ký hoạt động'
        indexes = [
            models.Index(fields=['user', '-created_at'], name='activity_user_time_idx'),
            models.Index(fields=['-created_at'],         name='activity_time_idx'),
            models.Index(fields=['model_name'],          name='activity_model_idx'),
            models.Index(fields=['action_type'],         name='activity_action_idx'),
        ]
 
    def __str__(self):
        who = self.user.username if self.user else 'Ẩn danh'
        return f"{who} {self.get_action_type_display()} {self.model_name} @ {self.created_at:%d/%m/%Y %H:%M}"
 
    @property
    def action_color(self):
        return {
            'VIEW':   'info',
            'CREATE': 'success',
            'UPDATE': 'warning',
            'DELETE': 'danger',
            'EXPORT': 'secondary',
            'IMPORT': 'primary',
            'LOGIN':  'dark',
        }.get(self.action_type, 'secondary')
 
 
# ── 3. Session đang active (ai đang online) ────────────────
class ActiveSession(models.Model):
    user          = models.OneToOneField(User, on_delete=models.CASCADE,
                       related_name='active_session', verbose_name='Người dùng')
    session_key   = models.CharField(max_length=40, unique=True, verbose_name='Session key')
    ip_address    = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP')
    user_agent    = models.TextField(blank=True, verbose_name='Trình duyệt')
    last_activity = models.DateTimeField(auto_now=True, verbose_name='Hoạt động cuối')
    login_at      = models.DateTimeField(auto_now_add=True, verbose_name='Đăng nhập lúc')
    current_page  = models.CharField(max_length=200, blank=True, verbose_name='Trang hiện tại')
 
    class Meta:
        db_table             = 'active_session'
        verbose_name         = 'Phiên đang hoạt động'
        verbose_name_plural  = 'Phiên đang hoạt động'
 
    def __str__(self):
        return f"{self.user.username} online từ {self.login_at:%H:%M %d/%m/%Y}"
 
    @property
    def is_recently_active(self):
        """Online nếu có hoạt động trong 5 phút gần đây."""
        return (timezone.now() - self.last_activity).seconds < 300
 
    @property
    def duration(self):
        """Thời gian đã online."""
        delta = timezone.now() - self.login_at
        minutes = delta.seconds // 60
        if minutes < 60:
            return f"{minutes} phút"
        hours = minutes // 60
        mins  = minutes % 60
        return f"{hours}h{mins:02d}p"