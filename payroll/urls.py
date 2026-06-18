from django.urls import path
from . import views

app_name='payroll'
urlpatterns = [
    path('', views.du_an_list, name='du_an_list'),
    path('sheet/', views.payroll_sheet, name='payroll_sheet'),
    # Hỗ trợ gõ Sheet/ có chữ hoa
    path('Sheet/', views.payroll_sheet),
    path('statistics/', views.payroll_statistics, name='payroll_statistics'),
    path('seniority/', views.seniority_table, name='seniority_table'),
    path('tet-bonus-2025/', views.tet_bonus_2025, name='tet_bonus_2025'),
    path('add-employee/', views.add_employee, name='add_employee'),
    path('edit-employee/<int:pk>/', views.edit_employee, name='edit_employee'),
    path('delete-employee/<int:pk>/', views.delete_employee, name='delete_employee'),
    path('save/', views.save_attendance, name='save_attendance'),
    path('import-excel/', views.import_excel, name='import_excel'),
    path('api/log-adjustment/<int:employee_id>/', views.get_adjustment_logs, name='get_adjustment_logs'),
    path('delete-all/', views.delete_all_data, name='delete_all_data'),
    # Manager routes
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/create-user/', views.create_user, name='create_user'),
    path('manager/edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('manager/toggle-status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('manager/reset-password/<int:user_id>/', views.reset_user_password, name='reset_user_password'),
    path('manager/delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    
    # User routes
    path('user/change-password/', views.change_own_password, name='change_own_password'),

    # Project management routes
    path('projects/create/', views.du_an_create, name='du_an_create'),
    path('projects/<int:pk>/', views.du_an_detail, name='du_an_detail'),
    path('projects/<int:pk>/edit/', views.du_an_edit, name='du_an_edit'),
    path('projects/<int:pk>/delete/', views.du_an_delete, name='du_an_delete'),
    path('tong-hop-2026/', views.tong_hop_2026, name='tong_hop_2026'),

    # User tracking routes
    path('manager/user-tracking/', views.user_tracking_dashboard, name='user_tracking_dashboard'),
    path('manager/user-tracking/<int:user_id>/', views.user_tracking_detail, name='user_tracking_detail'),
    path('api/online-users/', views.api_online_users, name='api_online_users'),
]
