from django.db import models

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
    ten_cong_trinh = models.CharField(max_length=255, verbose_name ="tên công trình")
    dia_diem = models.CharField (max_length=255, blank=True, null=True, verbose_name="địa điểm")

    class Meta:
        db_table = "cong_trinh"
        verbose_name = "công trình"
        verbose_name_plural = "Danh sách công trình"

    def __str__(self):
        return self.ten_cong_trinh


#2 bản quản ly nhân viên
class NhanVien (models.Model):
    ho_ten = models.CharField(max_length=100, verbose_name="Họ và tên")
    so_dien_thoai = models.CharField(max_length=15, blank=True, null=True, verbose_name="Số điện thoại")

    class Meta:
        db_table = "nhan_vien"
        verbose_name = "Nhân viên "
        verbose_name_plural = "Danh sách nhân viên"

    def __str__(self):
        return self.ho_ten


# 3. Bảng danh mục Nghề và Đơn giá lương cơ sở
class DanhMucNghe(models.Model):
    ten_nghe = models.CharField(max_length=100, verbose_name="Tên nghề/Chức vụ")
    luong_ngay = models.FloatField(default=0.0, verbose_name="Lương ngày cơ sở (Công HC)")

    class Meta:
        db_table = 'danh_muc_nghe'
        verbose_name = "Danh mục nghề"
        verbose_name_plural = "Danh mục Nghề & Lương"

    def __str__(self):
        return f"{self.ten_nghe} ({self.luong_ngay:,} đ)"


# 4. Bảng chấm công chi tiết hàng ngày
class ChamCongHangNgay(models.Model):
    ngay = models.DateField(verbose_name="Ngày chấm công")
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name="ds_cham_cong")
    cong_trinh = models.ForeignKey(CongTrinh, on_delete=models.CASCADE, related_name="ds_cham_cong")
    nghe = models.ForeignKey(DanhMucNghe, on_delete=models.PROTECT, verbose_name="Nghề thực tế ngày này")
    so_cong_hc = models.FloatField(default=0.0, verbose_name="Số công Hành Chính")
    so_cong_tc = models.FloatField(default=0.0, verbose_name="Số công Tăng Ca")

    class Meta:
        db_table = 'cham_cong_hang_ngay'
        # Ràng buộc UNIQUE để tránh chấm trùng cho 1 người/ngày/công trình
        unique_together = ('nhan_vien', 'ngay', 'cong_trinh')
        verbose_name = "Chấm công ngày"
        verbose_name_plural = "Chấm công hàng ngày"

    def __str__(self):
        return f"{self.nhan_vien.ho_ten} - {self.ngay} (HC: {self.so_cong_hc}, TC: {self.so_cong_tc})"


# 5. Bảng lưu trữ Thưởng/Phạt (Tăng/Giảm)
class PhuThuThuongPhat(models.Model):
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name="ds_phu_thu")
    cong_trinh = models.ForeignKey(CongTrinh, on_delete=models.CASCADE, related_name="ds_phu_thu")
    ngay_ghi_nhan = models.DateField(verbose_name="Ngày ghi nhận (Thường chốt cuối tuần)")
    so_tien_tang = models.FloatField(default=0.0, verbose_name="Số tiền tăng (Thưởng/Phụ cấp)")
    so_tien_giam = models.FloatField(default=0.0, verbose_name="Số tiền giảm (Phạt/Tạm ứng)")

    class Meta:
        db_table = 'phu_thu_thuong_phat'
        verbose_name = "Thưởng phạt phụ thu"
        verbose_name_plural = "Quản lý Tăng/Giảm"

    def __str__(self):
        return f"{self.nhan_vien.ho_ten} (+{self.so_tien_tang:,} | -{self.so_tien_giam:,})"


# 6. Bảng chốt công và lương theo THÁNG
class ChotLuongThang(models.Model):
    TRANG_THAI_CHOICES = [
        ('NHAP', 'Dự thảo (Chưa khóa)'),
        ('CHOT', 'Đã chốt (Khóa sổ)'),
    ]

    thang_nam = models.CharField(max_length=7, verbose_name="Tháng Năm (Định dạng YYYY-MM)")
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name="ds_luong_thang")
    cong_trinh = models.ForeignKey(CongTrinh, on_delete=models.CASCADE, related_name="ds_luong_thang")

    tong_cong_hc = models.FloatField(default=0.0, verbose_name="Tổng công HC")
    tong_cong_tc = models.FloatField(default=0.0, verbose_name="Tổng công TC")

    tong_tien_luong_goc = models.FloatField(default=0.0, verbose_name="Tổng tiền lương gốc")
    tong_tien_tang = models.FloatField(default=0.0, verbose_name="Tổng thưởng/Tăng")
    tong_tien_giam = models.FloatField(default=0.0, verbose_name="Tổng phạt/Giảm")
    thuc_lanh_thang = models.FloatField(default=0.0, verbose_name="Thực lĩnh tháng")

    trang_thai = models.CharField(max_length=10, choices=TRANG_THAI_CHOICES, default='NHAP', verbose_name="Trạng thái")
    ngay_chot = models.DateTimeField(auto_now=True, verbose_name="Ngày thực hiện chốt")

    class Meta:
        db_table = 'chot_luong_thang'
        # Đảm bảo mỗi nhân viên tại một công trình chỉ chốt lương 1 lần duy nhất trong tháng
        unique_together = ('thang_nam', 'nhan_vien', 'cong_trinh')
        verbose_name = "Chốt lương tháng"
        verbose_name_plural = "Bảng chốt lương tháng"

    def __str__(self):
        return f"{self.nhan_vien.ho_ten} - Tháng {self.thang_nam} ({self.trang_thai})"