from django.contrib import admin
from .models import Employee, Attendance, Adjustment

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
