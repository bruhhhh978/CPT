from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class UserTrackingMiddleware(MiddlewareMixin):

    SKIP_PATHS = ('/static/', '/media/', '/favicon.ico', '/admin/jsi18n/',
                  '/api/online-users/')

    # Mapping path → (action_type, model_name, mô tả)
    ACTION_MAP = [
        # Tài khoản
        ('manager/create-user',         'CREATE', 'TaiKhoan',  'Tạo tài khoản mới'),
        ('manager/edit-user',           'UPDATE', 'TaiKhoan',  'Chỉnh sửa tài khoản'),
        ('manager/delete-user',         'DELETE', 'TaiKhoan',  'Xóa tài khoản'),
        ('manager/toggle-status',       'UPDATE', 'TaiKhoan',  'Khóa/mở khóa tài khoản'),
        ('manager/reset-user-password', 'UPDATE', 'TaiKhoan',  'Đặt lại mật khẩu'),
        ('user/change-password',        'UPDATE', 'TaiKhoan',  'Đổi mật khẩu'),
        # Nhân viên
        ('add-employee',                'CREATE', 'NhanVien',  'Thêm nhân viên'),
        ('edit-employee',               'UPDATE', 'NhanVien',  'Sửa nhân viên'),
        ('delete-employee',             'DELETE', 'NhanVien',  'Xóa nhân viên'),
        # Công trình / dự án
        ('projects/create',             'CREATE', 'CongTrinh', 'Tạo công trình'),
        ('projects',                    'UPDATE', 'CongTrinh', 'Sửa công trình'),
        # Chấm công
        ('save',                        'UPDATE', 'ChamCong',  'Lưu dữ liệu chấm công'),
        ('import-excel',                'IMPORT', 'ChamCong',  'Import file Excel'),
        ('delete-all',                  'DELETE', 'ChamCong',  'Xóa toàn bộ dữ liệu'),
        # Xuất file
        ('export',                      'EXPORT', '',          'Xuất file Excel'),
    ]

    # Mapping path → tên trang đẹp
    PAGE_MAP = [
        ('manager/user-tracking',   '🔍 Theo dõi người dùng'),
        ('manager/dashboard',       '⚙️ Quản lý hệ thống'),
        ('manager/create-user',     '➕ Tạo tài khoản'),
        ('manager/edit-user',       '✏️ Sửa tài khoản'),
        ('manager/delete-user',     '🗑️ Xóa tài khoản'),
        ('projects/create',         '➕ Tạo công trình'),
        ('projects',                '🏗️ Dự án'),
        ('tong-hop-2026',           '📊 Tổng hợp 2026'),
        ('statistics',              '📈 Thống kê'),
        ('import-excel',            '📥 Import Excel'),
        ('save',                    '💾 Lưu chấm công'),
        ('sheet',                   '📋 Bảng chấm công'),
        ('login',                   '🔐 Đăng nhập'),
    ]

    def process_request(self, request):
        if not request.user.is_authenticated:
            return
        if any(request.path.startswith(p) for p in self.SKIP_PATHS):
            return

        from login.models import ActiveSession, UserActivityLog

        ip = self._get_ip(request)
        path = request.path
        page_label = self._get_page_label(path)
        session_key = request.session.session_key or ''

        # Cập nhật ActiveSession
        ActiveSession.objects.update_or_create(
            user=request.user,
            defaults=dict(
                session_key  = session_key,
                ip_address   = ip,
                user_agent   = request.META.get('HTTP_USER_AGENT', '')[:500],
                current_page = page_label,
            )
        )

        # Dọn session quá 30 phút
        cutoff = timezone.now() - timezone.timedelta(minutes=30)
        ActiveSession.objects.filter(
            last_activity__lt=cutoff
        ).exclude(user=request.user).delete()

        # Chỉ ghi activity log cho POST request (thao tác thực sự)
        if request.method != 'POST':
            return

        # Bỏ qua CSRF token-only POST
        action_type, model_name, description = self._get_action(path, request)
        if not action_type:
            return

        UserActivityLog.objects.create(
            user        = request.user,
            action_type = action_type,
            model_name  = model_name,
            path        = path,
            description = description,
            ip_address  = ip,
        )

    # ── Helpers ───────────────────────────────────────────

    def _get_ip(self, request):
        x_fwd = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_fwd:
            return x_fwd.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def _get_page_label(self, path):
        path_lower = path.lower()
        for key, label in self.PAGE_MAP:
            if key in path_lower:
                return label
        return path[:100]

    def _get_action(self, path, request):
        path_lower = path.lower()

        # Xuất Excel — GET request có ?export=excel
        if request.method == 'GET' and request.GET.get('export') == 'excel':
            return 'EXPORT', '', 'Xuất file Excel bảng lương'

        for key, action, model, desc in self.ACTION_MAP:
            if key in path_lower:
                # Thêm chi tiết từ POST data nếu có
                detail = self._get_post_detail(request, action)
                full_desc = f"{desc}{detail}"
                return action, model, full_desc

        return None, None, None

    def _get_post_detail(self, request, action):
        """Lấy thêm thông tin chi tiết từ POST data."""
        try:
            # Tên user khi tạo/sửa tài khoản
            username = request.POST.get('username', '')
            if username:
                return f': {username}'

            # Tên nhân viên
            name = request.POST.get('name', '')
            if name:
                return f': {name}'

            # Tháng chấm công
            current_date = request.POST.get('current_date', '')
            if current_date:
                return f' tháng {current_date[5:7]}/{current_date[:4]}'

        except Exception:
            pass
        return ''