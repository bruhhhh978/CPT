from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from .models import UserProfile

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Check if user is manager and redirect to dashboard
            try:
                if user.profile.role == 'manager':
                    return redirect(reverse('payroll:manager_dashboard'))
            except:
                pass
            return redirect(reverse('payroll:payroll_sheet'))  
        else:
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng.')
    return render(request, 'login/login.html')

def logout_view(request):
    logout(request)
    return redirect('login:login')