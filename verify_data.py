from payroll.models import NhanVien, CongTrinh, DanhMucNghe, ChamCongHangNgay, PhuThuThuongPhat
print("=" * 60)
print("✓ NEW MODELS DATA VERIFICATION")
print("=" * 60)
print(f"\nCongTrinh count: {CongTrinh.objects.count()}")
for ct in CongTrinh.objects.all():
    print(f"  - {ct.ten_cong_trinh} ({ct.dia_diem})")

print(f"\nNhanVien count: {NhanVien.objects.count()}")
print("  Sample employees:")
for nv in NhanVien.objects.all()[:5]:
    print(f"    - {nv.ho_ten}")

print(f"\nDanhMucNghe count: {DanhMucNghe.objects.count()}")
for dmn in DanhMucNghe.objects.all():
    print(f"  - {dmn.ten_nghe}: {dmn.luong_ngay}đ")

print(f"\nChamCongHangNgay count: {ChamCongHangNgay.objects.count()}")
print("  Sample records:")
for cc in ChamCongHangNgay.objects.all()[:3]:
    print(f"    - {cc.nhan_vien.ho_ten} ({cc.ngay}): HC={cc.so_cong_hc}, TC={cc.so_cong_tc}")

print(f"\nPhuThuThuongPhat count: {PhuThuThuongPhat.objects.count()}")
for pt in PhuThuThuongPhat.objects.all():
    print(f"  - {pt.nhan_vien.ho_ten}: +{pt.so_tien_tang}đ, -{pt.so_tien_giam}đ")

print("\n" + "=" * 60)
print("✅ Verification complete!")
print("=" * 60)
