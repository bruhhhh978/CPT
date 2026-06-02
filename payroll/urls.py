from django.urls import path
from . import views

app_name='payroll'
urlpatterns = [
    path('', views.payroll_sheet, name='payroll_sheet'),
    path('sheet/', views.payroll_sheet, name='payroll_sheet_alias'),
    path('statistics/', views.payroll_statistics, name='payroll_statistics'),
    path('add-employee/', views.add_employee, name='add_employee'),
    path('edit-employee/<int:pk>/', views.edit_employee, name='edit_employee'),
    path('delete-employee/<int:pk>/', views.delete_employee, name='delete_employee'),
    path('save/', views.save_attendance, name='save_attendance'),
    path('import-excel/', views.import_excel, name='import_excel'),
    path('delete-all/', views.delete_all_data, name='delete_all_data'),
    
    # Manager routes
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/create-user/', views.create_user, name='create_user'),
    path('manager/edit-user/<int:user_id>/', views.edit_user_role, name='edit_user_role'),
    path('manager/delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
]
