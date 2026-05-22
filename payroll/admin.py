from django.contrib import admin
from .models import Employee, Attendance, Adjustment
from .models import CongTrinh, NhanVien, DanhMucNghe, ChamCongHangNgay, PhuThuThuongPhat, ChotLuongThang

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'date_of_birth', 'position', 'daily_wage')
    search_fields = ('name',)
    list_filter = ('date_of_birth', 'position')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'regular_workday', 'overtime_workday')
    list_filter = ('date', 'employee')

@admin.register(Adjustment)
class AdjustmentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'start_date', 'end_date', 'amount')

#data
@admin.register(CongTrinh)
class CongTrinhAdmin(admin.ModelAdmin):
    list_display = ('id', 'ten_cong_trinh', 'dia_diem')
    search_fields = ('ten_cong_trinh',)

@admin.register(NhanVien)
class NhanVienAdmin(admin.ModelAdmin):
    list_display = ('id', 'ho_ten', 'so_dien_thoai')
    search_fields = ('ho_ten', 'so_dien_thoai')

@admin.register(DanhMucNghe)
class DanhMucNgheAdmin(admin.ModelAdmin):
    list_display = ('id', 'ten_nghe', 'display_luong')
    search_fields = ('ten_nghe',)

    def display_luong(self, obj):
        return f"{obj.luong_ngay:,} đ"
    display_luong.short_description = "Lương ngày"

@admin.register(ChamCongHangNgay)
class ChamCongHangNgayAdmin(admin.ModelAdmin):
    list_display = ('ngay', 'nhan_vien', 'cong_trinh', 'nghe', 'so_cong_hc', 'so_cong_tc')
    list_filter = ('ngay', 'cong_trinh', 'nghe')
    search_fields = ('nhan_vien__ho_ten',)

@admin.register(PhuThuThuongPhat)
class PhuThuThuongPhatAdmin(admin.ModelAdmin):
    list_display = ('ngay_ghi_nhan', 'nhan_vien', 'cong_trinh', 'so_tien_tang', 'so_tien_giam')
    list_filter = ('cong_trinh', 'ngay_ghi_nhan')

@admin.register(ChotLuongThang)
class ChotLuongThangAdmin(admin.ModelAdmin):
    list_display = ('thang_nam', 'nhan_vien', 'cong_trinh', 'thuc_lanh_thang', 'trang_thai', 'ngay_chot')
    list_filter = ('thang_nam', 'cong_trinh', 'trang_thai')