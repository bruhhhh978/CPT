from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class UserTrackingMiddleware(MiddlewareMixin):

    SKIP_PATHS = ('/static/', '/media/', '/favicon.ico', '/admin/jsi18n/',
                  '/api/online-users/', '/manager/user-tracking/')

    # Tất cả các action — cả GET lẫn POST
    ACTION_MAP = [
        # ── Tài khoản ──────────────────────────────────────
        ('manager/create-user',    'POST',  'CREATE', 'TaiKhoan',  'Tạo tài khoản mới'),
        ('manager/edit-user',      'POST',  'UPDATE', 'TaiKhoan',  'Chỉnh sửa tài khoản'),
        ('manager/delete-user',    'POST',  'DELETE', 'TaiKhoan',  'Xóa tài khoản'),
        ('manager/toggle-status',  'POST',  'UPDATE', 'TaiKhoan',  'Khóa/mở khóa tài khoản'),
        ('manager/reset-password', 'POST',  'UPDATE', 'TaiKhoan',  'Đặt lại mật khẩu'),
        ('user/change-password',   'POST',  'UPDATE', 'TaiKhoan',  'Đổi mật khẩu'),
        ('manager/dashboard',      'GET',   'VIEW',   'TaiKhoan',  'Xem trang quản lý hệ thống'),

        # ── Nhân viên ──────────────────────────────────────
        ('add-employee',           'POST',  'CREATE', 'NhanVien',  'Thêm nhân viên'),
        ('edit-employee',          'POST',  'UPDATE', 'NhanVien',  'Sửa nhân viên'),
        ('delete-employee',        'POST',  'DELETE', 'NhanVien',  'Xóa nhân viên'),

        # ── Công trình ─────────────────────────────────────
        ('projects/create',        'POST',  'CREATE', 'CongTrinh', 'Tạo công trình mới'),
        ('projects',               'GET',   'VIEW',   'CongTrinh', 'Xem danh sách dự án'),
        ('projects',               'POST',  'UPDATE', 'CongTrinh', 'Cập nhật công trình'),

        # ── Chấm công ──────────────────────────────────────
        ('save',                   'POST',  'UPDATE', 'ChamCong',  'Lưu dữ liệu chấm công'),
        ('import-excel',           'POST',  'IMPORT', 'ChamCong',  'Import file Excel'),
        ('delete-all',             'POST',  'DELETE', 'ChamCong',  'Xóa toàn bộ dữ liệu'),
        ('sheet',                  'GET',   'VIEW',   'ChamCong',  'Xem bảng chấm công'),
        ('Sheet',                  'GET',   'VIEW',   'ChamCong',  'Xem bảng chấm công'),

        # ── Thống kê / Báo cáo ─────────────────────────────
        ('statistics',             'GET',   'VIEW',   'ThongKe',   'Xem thống kê'),
        ('tong-hop-2026',          'GET',   'VIEW',   'ThongKe',   'Xem tổng hợp 2026'),

        # ── Xuất Excel ─────────────────────────────────────
        ('export',                 'GET',   'EXPORT', 'BaoCao',    'Xuất file Excel'),
    ]

    PAGE_MAP = [
        ('manager/user-tracking',  '🔍 Theo dõi người dùng'),
        ('manager/dashboard',      '⚙️ Quản lý hệ thống'),
        ('manager/create-user',    '➕ Tạo tài khoản'),
        ('manager/edit-user',      '✏️ Sửa tài khoản'),
        ('manager/delete-user',    '🗑️ Xóa tài khoản'),
        ('manager/toggle-status',  '🔒 Khóa/mở tài khoản'),
        ('manager/reset-password', '🔑 Đặt lại mật khẩu'),
        ('user/change-password',   '🔑 Đổi mật khẩu'),
        ('projects/create',        '➕ Tạo công trình'),
        ('projects',               '🏗️ Dự án'),
        ('tong-hop-2026',          '📊 Tổng hợp 2026'),
        ('statistics',             '📈 Thống kê'),
        ('import-excel',           '📥 Import Excel'),
        ('save',                   '💾 Lưu chấm công'),
        ('sheet',                  '📋 Bảng chấm công'),
        ('Sheet',                  '📋 Bảng chấm công'),
        ('login',                  '🔐 Đăng nhập'),
    ]

    def process_request(self, request):
        if not request.user.is_authenticated:
            return
        if any(request.path.startswith(p) for p in self.SKIP_PATHS):
            return

        from login.models import ActiveSession

        ip = self._get_ip(request)
        page_label = self._get_page_label(request.path)

        # Cập nhật ActiveSession (ai đang online, đang xem trang nào)
        ActiveSession.objects.update_or_create(
            user=request.user,
            defaults=dict(
                session_key  = request.session.session_key or '',
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

    def process_response(self, request, response):
        """Ghi log SAU KHI view xử lý xong."""
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return response
        if any(request.path.startswith(p) for p in self.SKIP_PATHS):
            return response

        from login.models import UserActivityLog

        method = request.method
        path   = request.path
        ip     = self._get_ip(request)

        # GET → chỉ ghi nếu response 200 (trang load thành công)
        # POST → chỉ ghi nếu response 302 (redirect = xử lý thành công)
        if method == 'GET' and response.status_code != 200:
            return response
        if method == 'POST' and response.status_code != 302:
            return response

        # Xuất Excel — GET có ?export=excel
        if method == 'GET' and request.GET.get('export') == 'excel':
            UserActivityLog.objects.create(
                user        = request.user,
                action_type = 'EXPORT',
                model_name  = 'BaoCao',
                path        = path,
                description = 'Xuất file Excel bảng lương',
                ip_address  = ip,
            )
            return response

        action_type, model_name, description = self._match_action(path, method, request)
        if not action_type:
            return response

        UserActivityLog.objects.create(
            user        = request.user,
            action_type = action_type,
            model_name  = model_name,
            path        = path,
            description = description,
            ip_address  = ip,
        )

        return response

    # ── Helpers ───────────────────────────────────────────

    def _match_action(self, path, method, request):
        path_lower = path.lower()
        for key, req_method, action, model, desc in self.ACTION_MAP:
            if key.lower() in path_lower and req_method == method:
                detail = self._get_detail(request, action)
                return action, model, f"{desc}{detail}"
        return None, None, None

    def _get_detail(self, request, action):
        """Lấy thêm thông tin từ POST/GET để mô tả chi tiết hơn."""
        try:
            if request.method == 'POST':
                for field in ('username', 'name', 'ten_cong_trinh'):
                    val = request.POST.get(field, '').strip()
                    if val:
                        return f': {val}'
                date = request.POST.get('current_date', '')
                if date:
                    return f' tháng {date[5:7]}/{date[:4]}'
            if request.method == 'GET':
                date = request.GET.get('date', '')
                if date:
                    return f' ({date})'
        except Exception:
            pass
        return ''

    def _get_ip(self, request):
        x_fwd = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_fwd:
            return x_fwd.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def _get_page_label(self, path):
        path_lower = path.lower()
        for key, label in self.PAGE_MAP:
            if key.lower() in path_lower:
                return label
        return path[:100]