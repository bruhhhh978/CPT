from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
import re

class Employee(models.Model):
    POSITION_CHOICES = [
        ('Cai', 'Cai (Cai quản)'),
        ('Tho', 'Thợ'),
        ('Phu', 'Phụ'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Họ tên")
    date_of_birth = models.DateField(blank=True, null=True, verbose_name="Ngày sinh")
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, verbose_name="Nghề")
    daily_wage = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Tiền công (1 ngày)")

    def __str__(self):
        return f"{self.name} ({self.position})"

    class Meta:
        verbose_name = "Nhân viên"
        verbose_name_plural = "Nhân viên"

class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(verbose_name="Ngày")
    # In the image, they use 'x' for 1.0, '\' for 0.5
    regular_workday = models.DecimalField(max_digits=3, decimal_places=1, default=0.0, verbose_name="Công HC")
    overtime_workday = models.DecimalField(max_digits=3, decimal_places=1, default=0.0, verbose_name="Công TC")
    
    class Meta:
        unique_together = ('employee', 'date')
        verbose_name = "Chấm công"
        verbose_name_plural = "Chấm công"

class Adjustment(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='adjustments')
    start_date = models.DateField()
    end_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Tăng/Giảm")
    note = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ghi chú")

    class Meta:
        verbose_name = "Tăng giảm lương"
        verbose_name_plural = "Tăng giảm lương"

#1 bản quán lý công trình
class CongTrinh(models.Model):
    TRANG_THAI_CHOICES = [
        ('MOI', 'Mới tạo'),
        ('DANG_THI_CONG', 'Đang thi công'),
        ('TAM_DUNG', 'Tạm dừng'),
        ('HOAN_THANH', 'Hoàn thành'),
    ]
    ten_cong_trinh = models.CharField(max_length=255, verbose_name="Tên công trình", unique=True)
    dia_diem = models.CharField(max_length=255, blank=True, null=True, verbose_name="Địa điểm")
    ngay_bat_dau = models.DateField(default=timezone.now, verbose_name="Ngày bắt đầu")
    thoi_han_ket_thuc = models.DateField(blank=True, null=True, verbose_name="Thời hạn kết thúc")
    mo_ta = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='MOI', verbose_name="Trạng thái")

    class Meta:
        db_table = "cong_trinh"
        verbose_name = "công trình"
        verbose_name_plural = "Danh sách công trình"

    def clean(self):
        # Validate no empty name
        if not self.ten_cong_trinh or not self.ten_cong_trinh.strip():
            raise ValidationError({'ten_cong_trinh': 'Tên công trình không được rỗng'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def get_status_display_color(self):
        """Trả về mã màu cho từng trạng thái dự án"""
        colors = {
            'MOI': '#0dcaf0',         # Xanh nhạt (Info)
            'DANG_THI_CONG': '#198754', # Xanh lá (Success)
            'TAM_DUNG': '#ffc107',     # Vàng (Warning)
            'HOAN_THANH': '#6c757d',    # Xám (Secondary)
        }
        return colors.get(self.trang_thai, '#000000')

    def __str__(self):
        return self.ten_cong_trinh


#2 bản quản ly nhân viên
class NhanVien(models.Model):
    ho_ten = models.CharField(max_length=100, verbose_name="Họ và tên", unique=True)
    so_dien_thoai = models.CharField(
        max_length=15, 
        blank=True, 
        null=True, 
        verbose_name="Số điện thoại",
        validators=[
            RegexValidator(
                regex=r'^[0-9]{10,11}$',
                message='Số điện thoại phải có 10-11 chữ số',
                code='invalid_phone'
            )
        ]
    )

    class Meta:
        db_table = "nhan_vien"
        verbose_name = "Nhân viên"
        verbose_name_plural = "Danh sách nhân viên"

    def clean(self):
        # Validate no empty name
        if not self.ho_ten or not self.ho_ten.strip():
            raise ValidationError({'ho_ten': 'Họ và tên không được rỗng'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ho_ten


# 3. Bảng danh mục Nghề và Đơn giá lương cơ sở
class DanhMucNghe(models.Model):
    ten_nghe = models.CharField(max_length=100, verbose_name="Tên nghề/Chức vụ", unique=True)
    luong_ngay = models.FloatField(
        default=0.0, 
        verbose_name="Lương ngày cơ sở (Công HC)",
        validators=[MinValueValidator(0, message='Lương phải >= 0')]
    )

    class Meta:
        db_table = 'danh_muc_nghe'
        verbose_name = "Danh mục nghề"
        verbose_name_plural = "Danh mục Nghề & Lương"

    def clean(self):
        if not self.ten_nghe or not self.ten_nghe.strip():
            raise ValidationError({'ten_nghe': 'Tên nghề không được rỗng'})
        if self.luong_ngay < 0:
            raise ValidationError({'luong_ngay': 'Lương phải >= 0'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ten_nghe} ({self.luong_ngay:,.0f} đ)"


# 4. Bảng chấm công chi tiết hàng ngày
class ChamCongHangNgay(models.Model):
    ngay = models.DateField(verbose_name="Ngày chấm công")
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name="ds_cham_cong")
    cong_trinh = models.ForeignKey(CongTrinh, on_delete=models.CASCADE, related_name="ds_cham_cong")
    nghe = models.ForeignKey(DanhMucNghe, on_delete=models.PROTECT, verbose_name="Nghề thực tế ngày này")
    so_cong_hc = models.FloatField(
        default=0.0, 
        verbose_name="Số công Hành Chính",
        validators=[
            MinValueValidator(0, message='Công không được âm'),
            MaxValueValidator(1, message='Công HC tối đa 1 ngày')
        ]
    )
    so_cong_tc = models.FloatField(
        default=0.0, 
        verbose_name="Số công Tăng Ca",
        validators=[
            MinValueValidator(0, message='Công TC không được âm'),
            MaxValueValidator(1, message='Công TC tối đa 1 ngày')
        ]
    )

    class Meta:
        db_table = 'cham_cong_hang_ngay'
        unique_together = ('nhan_vien', 'ngay', 'cong_trinh')
        verbose_name = "Chấm công ngày"
        verbose_name_plural = "Chấm công hàng ngày"
        indexes = [
            models.Index(fields=['ngay']),
            models.Index(fields=['nhan_vien', 'ngay']),
            models.Index(fields=['cong_trinh']),
        ]

    def clean(self):
        # Validate date not in future
        if self.ngay > timezone.now().date():
            raise ValidationError({'ngay': 'Ngày chấm công không thể trong tương lai'})
        
        # Validate so_cong_hc and so_cong_tc
        if self.so_cong_hc < 0 or self.so_cong_hc > 1:
            raise ValidationError({'so_cong_hc': 'Công HC phải từ 0 đến 1'})
        
        if self.so_cong_tc < 0 or self.so_cong_tc > 1:
            raise ValidationError({'so_cong_tc': 'Công TC phải từ 0 đến 1'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nhan_vien.ho_ten} - {self.ngay} (HC: {self.so_cong_hc}, TC: {self.so_cong_tc})"


# 5. Bảng lưu trữ Thưởng/Phạt (Tăng/Giảm)
class PhuThuThuongPhat(models.Model):
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name="ds_phu_thu")
    cong_trinh = models.ForeignKey(CongTrinh, on_delete=models.CASCADE, related_name="ds_phu_thu")
    ngay_ghi_nhan = models.DateField(verbose_name="Ngày ghi nhận (Thường chốt cuối tuần)")
    so_tien_tang = models.FloatField(
        default=0.0, 
        verbose_name="Số tiền tăng (Thưởng/Phụ cấp)",
        validators=[MinValueValidator(0, message='Số tiền tăng phải >= 0')]
    )
    so_tien_giam = models.FloatField(
        default=0.0, 
        verbose_name="Số tiền giảm (Phạt/Tạm ứng)",
        validators=[MinValueValidator(0, message='Số tiền giảm phải >= 0')]
    )

    class Meta:
        db_table = 'phu_thu_thuong_phat'
        verbose_name = "Thưởng phạt phụ thu"
        verbose_name_plural = "Quản lý Tăng/Giảm"
        indexes = [
            models.Index(fields=['ngay_ghi_nhan']),
            models.Index(fields=['nhan_vien']),
        ]

    def clean(self):
        if self.so_tien_tang < 0:
            raise ValidationError({'so_tien_tang': 'Số tiền tăng phải >= 0'})
        if self.so_tien_giam < 0:
            raise ValidationError({'so_tien_giam': 'Số tiền giảm phải >= 0'})
        if self.ngay_ghi_nhan > timezone.now().date():
            raise ValidationError({'ngay_ghi_nhan': 'Ngày ghi nhận không được trong tương lai'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nhan_vien.ho_ten} (+{self.so_tien_tang:,.0f} | -{self.so_tien_giam:,.0f})"


# 6. Bảng chốt công và lương theo THÁNG
class ChotLuongThang(models.Model):
    TRANG_THAI_CHOICES = [
        ('NHAP', 'Dự thảo (Chưa khóa)'),
        ('CHOT', 'Đã chốt (Khóa sổ)'),
    ]

    thang_nam = models.CharField(
        max_length=7, 
        verbose_name="Tháng Năm (Định dạng YYYY-MM)",
        validators=[
            RegexValidator(
                regex=r'^\d{4}-\d{2}$',
                message='Định dạng phải là YYYY-MM',
                code='invalid_format'
            )
        ]
    )
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name="ds_luong_thang")
    cong_trinh = models.ForeignKey(CongTrinh, on_delete=models.CASCADE, related_name="ds_luong_thang")

    tong_cong_hc = models.FloatField(
        default=0.0, 
        verbose_name="Tổng công HC",
        validators=[MinValueValidator(0)]
    )
    tong_cong_tc = models.FloatField(
        default=0.0, 
        verbose_name="Tổng công TC",
        validators=[MinValueValidator(0)]
    )

    tong_tien_luong_goc = models.FloatField(
        default=0.0, 
        verbose_name="Tổng tiền lương gốc",
        validators=[MinValueValidator(0)]
    )
    tong_tien_tang = models.FloatField(
        default=0.0, 
        verbose_name="Tổng thưởng/Tăng",
        validators=[MinValueValidator(0)]
    )
    tong_tien_giam = models.FloatField(
        default=0.0, 
        verbose_name="Tổng phạt/Giảm",
        validators=[MinValueValidator(0)]
    )
    thuc_lanh_thang = models.FloatField(
        default=0.0, 
        verbose_name="Thực lĩnh tháng",
        validators=[MinValueValidator(0)]
    )

    trang_thai = models.CharField(max_length=10, choices=TRANG_THAI_CHOICES, default='NHAP', verbose_name="Trạng thái")
    ngay_chot = models.DateTimeField(auto_now=True, verbose_name="Ngày thực hiện chốt")

    class Meta:
        db_table = 'chot_luong_thang'
        unique_together = ('thang_nam', 'nhan_vien', 'cong_trinh')
        verbose_name = "Chốt lương tháng"
        verbose_name_plural = "Bảng chốt lương tháng"
        indexes = [
            models.Index(fields=['thang_nam']),
            models.Index(fields=['nhan_vien']),
        ]

    def clean(self):
        # Validate thang_nam format
        if not re.match(r'^\d{4}-\d{2}$', self.thang_nam):
            raise ValidationError({'thang_nam': 'Định dạng phải là YYYY-MM (vd: 2026-05)'})
        
        # Validate year and month
        try:
            year, month = self.thang_nam.split('-')
            year = int(year)
            month = int(month)
            if month < 1 or month > 12:
                raise ValidationError({'thang_nam': 'Tháng phải từ 01 đến 12'})
        except:
            raise ValidationError({'thang_nam': 'Định dạng không hợp lệ'})
        
        # Validate all amounts >= 0
        if self.tong_cong_hc < 0 or self.tong_cong_tc < 0:
            raise ValidationError('Công không được âm')
        
        if self.tong_tien_luong_goc < 0 or self.tong_tien_tang < 0 or self.tong_tien_giam < 0:
            raise ValidationError('Số tiền không được âm')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nhan_vien.ho_ten} - {self.thang_nam} ({self.trang_thai})"