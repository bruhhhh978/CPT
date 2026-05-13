from django.db import models

class Employee(models.Model):
    POSITION_CHOICES = [
        ('Cai', 'Cai (Cai quản)'),
        ('Tho', 'Thợ'),
        ('Phu', 'Phụ'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Họ tên")
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
