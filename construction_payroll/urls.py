from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from payroll import views as payroll_views
urlpatterns = [
    path("admin/", admin.site.urls),
    path('', RedirectView.as_view(pattern_name='payroll:payroll_sheet', permanent=False), name='home'),
    path('add-employee/', payroll_views.add_employee, name='legacy_add_employee'),
    path('edit-employee/<int:pk>/', payroll_views.edit_employee, name='legacy_edit_employee'),
    path('delete-employee/<int:pk>/', payroll_views.delete_employee, name='legacy_delete_employee'),
    path('save/', payroll_views.save_attendance, name='legacy_save_attendance'),
    path('import-excel/', payroll_views.import_excel, name='legacy_import_excel'),
    path('delete-all/', payroll_views.delete_all_data, name='legacy_delete_all_data'),
    path('statistics/', payroll_views.payroll_statistics, name='legacy_payroll_statistics'),
    path("payroll/", include("payroll.urls")),
    path('login/', include('login.urls')),
]
