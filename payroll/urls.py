from django.urls import path
from . import views

urlpatterns = [
    path('', views.payroll_sheet, name='payroll_sheet'),
    path('add-employee/', views.add_employee, name='add_employee'),
    path('edit-employee/<int:pk>/', views.edit_employee, name='edit_employee'),
    path('delete-employee/<int:pk>/', views.delete_employee, name='delete_employee'),
    path('save-attendance/', views.save_attendance, name='save_attendance'),
]
