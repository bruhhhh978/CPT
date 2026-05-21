from django.contrib import admin
from django.urls import path, include
from payroll import views as payroll_views
urlpatterns = [
    path("admin/", admin.site.urls),
    path('', payroll_views.payroll_sheet, name='home'),
    path("payroll/", include("payroll.urls")),
    path('login/', include('login.urls')),
]
