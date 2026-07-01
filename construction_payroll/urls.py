from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from payroll import views as payroll_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path('payroll/', include('payroll.urls')),
    path('', include('payroll.urls')),
    path('login/', include('login.urls')),
]
