from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from payroll import views as payroll_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', include(('payroll.urls', 'payroll'), namespace='payroll')),
    path('login/', include('login.urls')),
]
