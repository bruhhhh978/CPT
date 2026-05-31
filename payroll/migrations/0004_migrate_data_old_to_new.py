from django.db import migrations
from django.db.models import Avg

def migrate_data(apps, schema_editor):
    # Get models
    Employee = apps.get_model('payroll', 'Employee')
    Attendance = apps.get_model('payroll', 'Attendance')
    Adjustment = apps.get_model('payroll', 'Adjustment')
    
    CongTrinh = apps.get_model('payroll', 'CongTrinh')
    NhanVien = apps.get_model('payroll', 'NhanVien')
    DanhMucNghe = apps.get_model('payroll', 'DanhMucNghe')
    ChamCongHangNgay = apps.get_model('payroll', 'ChamCongHangNgay')
    PhuThuThuongPhat = apps.get_model('payroll', 'PhuThuThuongPhat')
    ChotLuongThang = apps.get_model('payroll', 'ChotLuongThang')

    print("=" * 60)
    print("STARTING DATA MIGRATION: OLD → NEW MODELS")
    print("=" * 60)

    # Step 1: Tạo default CongTrinh (Công trình mặc định)
    print("\n[STEP 1] Creating default CongTrinh...")
    cong_trinh_default, created = CongTrinh.objects.get_or_create(
        ten_cong_trinh="Công trình mặc định",
        defaults={"dia_diem": "Chưa xác định"}
    )
    print(f"  ✓ CongTrinh created/found: {cong_trinh_default.ten_cong_trinh}")

    # Step 2: Migrate Employee → NhanVien + DanhMucNghe
    print("\n[STEP 2] Migrating Employee → NhanVien + DanhMucNghe...")
    employees = Employee.objects.all()
    print(f"  Total employees to migrate: {employees.count()}")

    nhan_vien_map = {}  # old employee id → new nhan_vien
    position_map = {}   # position → danhmucnghe
    
    # Tạo DanhMucNghe từ unique positions
    for position_code, position_name in [
        ('Cai', 'Cai (Cai quản)'),
        ('Tho', 'Thợ'),
        ('Phu', 'Phụ'),
    ]:
        # Tính lương trung bình cho mỗi vị trí từ employees
        avg_wage = employees.filter(position=position_code).aggregate(
            avg=Avg('daily_wage')
        )['avg'] or 0
        
        danh_muc_nghe, _ = DanhMucNghe.objects.get_or_create(
            ten_nghe=position_name,
            defaults={"luong_ngay": avg_wage}
        )
        position_map[position_code] = danh_muc_nghe
        print(f"  ✓ Created DanhMucNghe: {danh_muc_nghe.ten_nghe} ({danh_muc_nghe.luong_ngay}đ)")

    # Migrate employees
    for emp in employees:
        nhan_vien, created = NhanVien.objects.get_or_create(
            ho_ten=emp.name,
            defaults={"so_dien_thoai": ""}
        )
        nhan_vien_map[emp.id] = nhan_vien
        
        if created:
            print(f"  ✓ Created NhanVien: {nhan_vien.ho_ten}")

    print(f"  Total NhanVien created: {len(nhan_vien_map)}")

    # Step 3: Migrate Attendance → ChamCongHangNgay
    print("\n[STEP 3] Migrating Attendance → ChamCongHangNgay...")
    attendances = Attendance.objects.all()
    print(f"  Total attendances to migrate: {attendances.count()}")
    
    created_count = 0
    for att in attendances:
        nhan_vien = nhan_vien_map.get(att.employee_id)
        if not nhan_vien:
            continue
        
        # Lấy position của employee từ old model
        old_emp = Employee.objects.get(id=att.employee_id)
        danh_muc_nghe = position_map.get(old_emp.position)
        
        if not danh_muc_nghe:
            continue
        
        cham_cong, created = ChamCongHangNgay.objects.get_or_create(
            nhan_vien=nhan_vien,
            ngay=att.date,
            cong_trinh=cong_trinh_default,
            nghe=danh_muc_nghe,
            defaults={
                "so_cong_hc": float(att.regular_workday),
                "so_cong_tc": float(att.overtime_workday),
            }
        )
        
        if created:
            created_count += 1

    print(f"  ✓ Total ChamCongHangNgay created: {created_count}")

    # Step 4: Migrate Adjustment → PhuThuThuongPhat
    print("\n[STEP 4] Migrating Adjustment → PhuThuThuongPhat...")
    adjustments = Adjustment.objects.all()
    print(f"  Total adjustments to migrate: {adjustments.count()}")
    
    created_count = 0
    for adj in adjustments:
        nhan_vien = nhan_vien_map.get(adj.employee_id)
        if not nhan_vien:
            continue
        
        # Nếu adjustment > 0 → tăng, < 0 → giảm
        phu_thu, created = PhuThuThuongPhat.objects.get_or_create(
            nhan_vien=nhan_vien,
            cong_trinh=cong_trinh_default,
            ngay_ghi_nhan=adj.end_date,  # Dùng end_date làm ngày ghi nhận
            defaults={
                "so_tien_tang": max(0, float(adj.amount)),
                "so_tien_giam": max(0, -float(adj.amount)),
            }
        )
        
        if created:
            created_count += 1

    print(f"  ✓ Total PhuThuThuongPhat created: {created_count}")

    print("\n" + "=" * 60)
    print("✅ DATA MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  - CongTrinh: 1")
    print(f"  - NhanVien: {len(nhan_vien_map)}")
    print(f"  - DanhMucNghe: {len(position_map)}")
    print(f"  - ChamCongHangNgay: {ChamCongHangNgay.objects.count()}")
    print(f"  - PhuThuThuongPhat: {PhuThuThuongPhat.objects.count()}")
    print(f"\nNext steps:")
    print(f"  1. Test the application with new models")
    print(f"  2. Update views.py to use new models")
    print(f"  3. Delete old models (Employee, Attendance, Adjustment)")
    print(f"  4. Create final migration to remove old models")

def reverse_migrate(apps, schema_editor):
    # Delete all data from new models
    CongTrinh = apps.get_model('payroll', 'CongTrinh')
    NhanVien = apps.get_model('payroll', 'NhanVien')
    DanhMucNghe = apps.get_model('payroll', 'DanhMucNghe')
    ChamCongHangNgay = apps.get_model('payroll', 'ChamCongHangNgay')
    PhuThuThuongPhat = apps.get_model('payroll', 'PhuThuThuongPhat')
    ChotLuongThang = apps.get_model('payroll', 'ChotLuongThang')
    
    print("\nReverting data migration...")
    CongTrinh.objects.all().delete()
    NhanVien.objects.all().delete()
    DanhMucNghe.objects.all().delete()
    ChamCongHangNgay.objects.all().delete()
    PhuThuThuongPhat.objects.all().delete()
    ChotLuongThang.objects.all().delete()
    print("✓ Data reverted")


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0003_add_new_models'),
    ]

    operations = [
        migrations.RunPython(migrate_data, reverse_migrate),
    ]
