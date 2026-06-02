import datetime
from urllib import request
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.db.models import Sum
from django.db.models import Q
from .models import Employee, Attendance, Adjustment
from decimal import Decimal
import pandas as pd
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Side, Font, PatternFill
from django.contrib.humanize.templatetags.humanize import intcomma
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from login.models import UserProfile
from .decorators import manager_only, user_and_manager, allow_viewer
from django.contrib import messages

# ============ MANAGER DASHBOARD & USER MANAGEMENT ============

@manager_only
def manager_dashboard(request):
    """Manager-only dashboard for managing users and system settings"""
    users = User.objects.all().select_related('profile')
    context = {
        'users': users,
        'user_count': users.count(),
        'manager_count': users.filter(profile__role='manager').count(),
        'user_count_role': users.filter(profile__role='user').count(),
        'viewer_count': users.filter(profile__role='viewer').count(),
    }
    return render(request, 'payroll/manager_dashboard.html', context)

@manager_only
def create_user(request):
    """Create new user account (manager only)"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'user')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        # Validation
        if not username or len(username) < 3:
            messages.error(request, 'Tên đăng nhập phải ít nhất 3 ký tự.')
            return redirect('payroll:manager_dashboard')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Tên đăng nhập đã tồn tại.')
            return redirect('payroll:manager_dashboard')
        
        if not password or len(password) < 6:
            messages.error(request, 'Mật khẩu phải ít nhất 6 ký tự.')
            return redirect('payroll:manager_dashboard')
        
        if role not in ['manager', 'user', 'viewer']:
            messages.error(request, 'Cấp độ không hợp lệ.')
            return redirect('payroll:manager_dashboard')
        
        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            
            # Create user profile with role
            UserProfile.objects.create(user=user, role=role)
            messages.success(request, f'Tạo tài khoản "{username}" với cấp "{role}" thành công.')
        except Exception as e:
            messages.error(request, f'Lỗi khi tạo tài khoản: {str(e)}')
        
        return redirect('payroll:manager_dashboard')
    
    return redirect('payroll:manager_dashboard')

@manager_only
def edit_user_role(request, user_id):
    """Edit user role (manager only)"""
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            # Prevent self-demotion
            if user == request.user and request.POST.get('role') != 'manager':
                messages.error(request, 'Bạn không thể hạ cấp chính mình.')
                return redirect('payroll:manager_dashboard')
            
            user.profile.role = request.POST.get('role', 'user')
            user.profile.save()
            messages.success(request, f'Cập nhật cấp độ cho "{user.username}" thành công.')
        except User.DoesNotExist:
            messages.error(request, 'Người dùng không tồn tại.')
        except Exception as e:
            messages.error(request, f'Lỗi khi cập nhật: {str(e)}')
    
    return redirect('payroll:manager_dashboard')

@manager_only
def delete_user(request, user_id):
    """Delete user account (manager only)"""
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            
            # Prevent self-deletion
            if user == request.user:
                messages.error(request, 'Bạn không thể xóa chính mình.')
                return redirect('payroll:manager_dashboard')
            
            username = user.username
            user.delete()
            messages.success(request, f'Xóa tài khoản "{username}" thành công.')
        except User.DoesNotExist:
            messages.error(request, 'Người dùng không tồn tại.')
        except Exception as e:
            messages.error(request, f'Lỗi khi xóa: {str(e)}')
    
    return redirect('payroll:manager_dashboard')

# ============ END MANAGER DASHBOARD ============

def get_week_range(date):
    # Excel file uses week range from Friday to Thursday.
    days_since_friday = (date.weekday() - 4) % 7
    friday = date - datetime.timedelta(days=days_since_friday)
    return [friday + datetime.timedelta(days=i) for i in range(7)]

def get_available_weeks():
    dates = Attendance.objects.values_list('date', flat=True).distinct()
    weeks = set()
    for d in dates:
        days_since_friday = (d.weekday() - 4) % 7
        friday = d - datetime.timedelta(days=days_since_friday)
        weeks.add(friday)
    return sorted(weeks)

def to_symbol(val):
    if val >= 1.0: return 'x'
    if val >= 0.5: return '/'
    return ''

def from_symbol(val):
    if val is None: return Decimal('0.0')
    val_str = str(val).strip().lower()
    if val_str == 'x': return Decimal('1.0')
    if val_str in ('/', '\\'): return Decimal('0.5')
    if not val_str: return Decimal('0.0')
    try:
        return Decimal(val_str)
    except:
        return Decimal('0.0')

def get_target_date(request):
    date_str = request.GET.get('date')
    if date_str:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    return timezone.now().date()

def get_weekday_label(date):
    lookup = {
        0: 'T2',
        1: 'T3',
        2: 'T4',
        3: 'T5',
        4: 'T6',
        5: 'T7',
        6: 'CN',
    }
    return lookup.get(date.weekday(), date.strftime('%a'))

def parse_attendance_input(value):
    if value is None:
        return Decimal('0.0')
    value_str = str(value).strip()
    if not value_str:
        return Decimal('0.0')
    try:
        return from_symbol(value_str)
    except Exception:
        try:
            return Decimal(value_str.replace(',', '.'))
        except Exception:
            return Decimal('0.0')

def get_search_type(request):
    search_type = request.GET.get('search_type', 'name').strip().lower()
    return search_type if search_type in ('name', 'dob') else 'name'

def get_filtered_employees(search_query='', search_type='name'):
    employees = Employee.objects.all().order_by('name')
    if search_query:
        employees = employees.filter(build_employee_search_query(search_query, search_type))
    return employees

def parse_birth_date_query(search_query):
    normalized_query = search_query.strip()
    for date_format in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y', '%d-%m-%y'):
        try:
            return {
                'match_type': 'full_date',
                'value': datetime.datetime.strptime(normalized_query, date_format).date(),
            }
        except ValueError:
            continue
    for date_format in ('%d/%m', '%d-%m'):
        try:
            parsed_date = datetime.datetime.strptime(normalized_query, date_format)
            return {
                'match_type': 'day_month',
                'day': parsed_date.day,
                'month': parsed_date.month,
            }
        except ValueError:
            continue
    return None

def build_employee_search_query(search_query, search_type='name'):
    if search_type == 'dob':
        birth_date_query = parse_birth_date_query(search_query)
        if not birth_date_query:
            return Q(pk__in=[])
        if birth_date_query['match_type'] == 'full_date':
            return Q(date_of_birth=birth_date_query['value'])
        return Q(date_of_birth__day=birth_date_query['day'], date_of_birth__month=birth_date_query['month'])
    return Q(name__icontains=search_query)

def build_weekly_payroll_data(employees, dates):
    start_date, end_date = dates[0], dates[-1]
    payroll_data = []

    for emp in employees:
        attendance_map = {
            att.date: att
            for att in Attendance.objects.filter(employee=emp, date__range=(start_date, end_date))
        }
        daily_atts = []
        total_hc = Decimal('0.0')
        total_tc = Decimal('0.0')

        for d in dates:
            att = attendance_map.get(d)
            hc = att.regular_workday if att else Decimal('0.0')
            tc = att.overtime_workday if att else Decimal('0.0')

            total_hc += hc
            total_tc += tc

            daily_atts.append({
                'date': d,
                'hc_symbol': to_symbol(hc) if hc > 0 else '',
                'tc_symbol': str(tc) if tc > 0 else ''
            })

        adj = Adjustment.objects.filter(employee=emp, start_date=start_date, end_date=end_date).first()
        adjustment_val = adj.amount if adj else Decimal('0.0')
        total_pay = (total_hc * emp.daily_wage) + (total_tc * (emp.daily_wage / Decimal('8'))) + adjustment_val

        payroll_data.append({
            'employee': emp,
            'daily_attendance': daily_atts,
            'total_hc': total_hc,
            'total_tc': total_tc,
            'adjustment': adjustment_val,
            'total_pay': total_pay
        })

    return payroll_data

def payroll_sheet(request):
    # Determine if user can edit (must be authenticated AND be manager/user)
    can_edit = False
    is_viewer_mode = True
    
    if request.user.is_authenticated:
        try:
            role = request.user.profile.role
            if role in ['manager', 'user']:
                can_edit = True
                is_viewer_mode = False
            # Viewer role logged in - can_edit stays False
        except:
            messages.error(request, 'Lỗi: Hồ sơ người dùng không hợp lệ.')
            return redirect('login:login')
    else:
        # Not authenticated - viewer mode (read-only)
        is_viewer_mode = True
        can_edit = False
    
    target_date = get_target_date(request)
    view_type = request.GET.get('view_type', 'week').strip().lower()
    if view_type not in ('week', 'month'):
        view_type = 'week'

    search_query = request.GET.get('q', '').strip()
    search_type = get_search_type(request)

    if view_type == 'month':
        import calendar
        first_day = target_date.replace(day=1)
        last_day = target_date.replace(day=calendar.monthrange(target_date.year, target_date.month)[1])
        dates = [first_day + datetime.timedelta(days=i) for i in range((last_day - first_day).days + 1)]
    else:
        dates = get_week_range(target_date)

    start_date, end_date = dates[0], dates[-1]

    if request.GET.get('export') == 'excel':
        # Only authenticated users can export
        if not request.user.is_authenticated:
            messages.error(request, 'Vui lòng đăng nhập để xuất Excel.')
            return redirect('login:login')
        return export_payroll_excel(dates, start_date, end_date, view_type)

    employees = get_filtered_employees(search_query, search_type)
    payroll_data = build_weekly_payroll_data(employees, dates)
    available_weeks = [
        {
            'start': w,
            'end': w + datetime.timedelta(days=6),
            'date_str': w.strftime('%Y-%m-%d'),
        }
        for w in get_available_weeks()
    ]

    date_headers = [
        {
            'date': d,
            'label': get_weekday_label(d),
            'display': f"{get_weekday_label(d)} {d.strftime('%d/%m')}"
        }
        for d in dates
    ]

    context = {
        'target_date': target_date,
        'dates': dates,
        'date_headers': date_headers,
        'start_date': start_date,
        'end_date': end_date,
        'prev_week': start_date - datetime.timedelta(days=7),
        'next_week': start_date + datetime.timedelta(days=7),
        'payroll_data': payroll_data,
        'search_query': search_query,
        'search_type': search_type,
        'available_weeks': available_weeks,
        'view_type': view_type,
        'current_month': target_date.strftime('%m'),
        'can_edit': can_edit,
        'is_viewer_mode': is_viewer_mode,
    }
    return render(request, 'payroll/payroll_sheet.html', context)

def payroll_statistics(request):
    # Determine if user can edit
    can_edit = False
    is_viewer_mode = True
    
    if request.user.is_authenticated:
        try:
            role = request.user.profile.role
            if role in ['manager', 'user']:
                can_edit = True
                is_viewer_mode = False
        except:
            messages.error(request, 'Lỗi: Hồ sơ người dùng không hợp lệ.')
            return redirect('login:login')
    else:
        is_viewer_mode = True
        can_edit = False
    
    target_date = get_target_date(request)
    search_query = request.GET.get('q', '').strip()
    search_type = get_search_type(request)
    dates = get_week_range(target_date)
    start_date, end_date = dates[0], dates[-1]

    employees = get_filtered_employees(search_query, search_type)
    payroll_data = build_weekly_payroll_data(employees, dates)

    total_hc = sum((row['total_hc'] for row in payroll_data), Decimal('0.0'))
    total_tc = sum((row['total_tc'] for row in payroll_data), Decimal('0.0'))
    total_pay = sum((row['total_pay'] for row in payroll_data), Decimal('0'))

    daily_totals = []
    for current_date in dates:
        daily_hc = Decimal('0.0')
        daily_tc = Decimal('0.0')
        for row in payroll_data:
            for att in row['daily_attendance']:
                if att['date'] == current_date:
                    daily_hc += from_symbol(att['hc_symbol'])
                    daily_tc += from_symbol(att['tc_symbol'])
                    break
        daily_totals.append({
            'label': current_date.strftime('%d/%m'),
            'hc': float(daily_hc),
            'tc': float(daily_tc),
        })

    chart_rows = [
        {
            'name': row['employee'].name,
            'hc': float(row['total_hc']),
            'tc': float(row['total_tc']),
        }
        for row in payroll_data
    ]

    available_weeks = [
        {
            'start': w,
            'end': w + datetime.timedelta(days=6),
            'date_str': w.strftime('%Y-%m-%d'),
        }
        for w in get_available_weeks()
    ]
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'prev_week': start_date - datetime.timedelta(days=7),
        'next_week': start_date + datetime.timedelta(days=7),
        'search_query': search_query,
        'search_type': search_type,
        'payroll_data': payroll_data,
        'employee_count': len(payroll_data),
        'total_hc': total_hc,
        'total_tc': total_tc,
        'total_pay': total_pay,
        'daily_totals': daily_totals,
        'chart_rows': chart_rows,
        'available_weeks': available_weeks,
        'can_edit': can_edit,
        'is_viewer_mode': is_viewer_mode,
    }
    return render(request, 'payroll/payroll_statistics.html', context)

def add_employee(request):
    # Check authorization - only users and managers can add
    if not request.user.is_authenticated:
        messages.error(request, 'Bạn phải đăng nhập để thực hiện chức năng này.')
        return redirect('login:login')
    
    try:
        role = request.user.profile.role
        if role not in ['manager', 'user']:
            messages.error(request, 'Bạn không có quyền thêm nhân viên.')
            return redirect('payroll:payroll_sheet')
    except:
        messages.error(request, 'Lỗi: Hồ sơ người dùng không hợp lệ.')
        return redirect('login:login')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        date_of_birth = request.POST.get('date_of_birth') or None
        pos = request.POST.get('position')
        wage = request.POST.get('daily_wage', 0)
        Employee.objects.create(
            name=name,
            date_of_birth=date_of_birth,
            position=pos,
            daily_wage=wage
        )
        messages.success(request, f'Đã thêm nhân viên "{name}" thành công.')
    return redirect('payroll:payroll_sheet')

def edit_employee(request, pk):
    # Check authorization - only users and managers can edit
    if not request.user.is_authenticated:
        messages.error(request, 'Bạn phải đăng nhập để thực hiện chức năng này.')
        return redirect('login:login')
    
    try:
        role = request.user.profile.role
        if role not in ['manager', 'user']:
            messages.error(request, 'Bạn không có quyền sửa nhân viên.')
            return redirect('payroll:payroll_sheet')
    except:
        messages.error(request, 'Lỗi: Hồ sơ người dùng không hợp lệ.')
        return redirect('login:login')
    
    emp = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        emp.name = request.POST.get('name')
        emp.date_of_birth = request.POST.get('date_of_birth') or None
        emp.position = request.POST.get('position')
        emp.daily_wage = request.POST.get('daily_wage')
        emp.save()
        messages.success(request, f'Đã cập nhật nhân viên "{emp.name}" thành công.')
    return redirect('payroll:payroll_sheet')

def delete_employee(request, pk):
    # Check authorization - only users and managers can delete
    if not request.user.is_authenticated:
        messages.error(request, 'Bạn phải đăng nhập để thực hiện chức năng này.')
        return redirect('login:login')
    
    try:
        role = request.user.profile.role
        if role not in ['manager', 'user']:
            messages.error(request, 'Bạn không có quyền xóa nhân viên.')
            return redirect('payroll:payroll_sheet')
    except:
        messages.error(request, 'Lỗi: Hồ sơ người dùng không hợp lệ.')
        return redirect('login:login')
    
    emp = get_object_or_404(Employee, pk=pk)
    emp_name = emp.name
    emp.delete()
    messages.success(request, f'Đã xóa nhân viên "{emp_name}" thành công.')
    return redirect('payroll:payroll_sheet')

def import_excel(request):
    # Check authorization - only managers can import
    if not request.user.is_authenticated:
        messages.error(request, 'Bạn phải đăng nhập để thực hiện chức năng này.')
        return redirect('login:login')
    
    try:
        role = request.user.profile.role
        if role != 'manager':
            messages.error(request, 'Chỉ quản lý mới có thể nhập file Excel.')
            return redirect('payroll:payroll_sheet')
    except:
        messages.error(request, 'Lỗi: Hồ sơ người dùng không hợp lệ.')
        return redirect('login:login')
    
    if request.method == 'POST' and request.FILES.get('excel_file'):
        from openpyxl import load_workbook
        import re

        excel_file = request.FILES['excel_file']
        wb = load_workbook(excel_file, data_only=True)

        for ws in wb.worksheets:
            sheet_name = ws.title.strip().lower()
            if 'tổng' in sheet_name or 'tong' in sheet_name:
                continue

            header_text = str(ws['G1'].value or '')

            date_matches = re.findall(r'(\d{1,2}/\d{1,2}/(?:\d{4}|\d{2}))', header_text)

            if not date_matches:
                continue
            raw_date = date_matches[0]

            try:
                try:
                    target_date = datetime.datetime.strptime(raw_date, '%d/%m/%Y').date()
                except ValueError:
                    target_date = datetime.datetime.strptime(raw_date, '%d/%m/%y').date()
            except Exception:
                continue
            
            dates = get_week_range(target_date)
            for row in ws.iter_rows(min_row=6):
                name = row[1].value
                if not name:
                    continue

                position = row[2].value
                emp, _ = Employee.objects.get_or_create(
                    name=name,
                    defaults={'position': position or 'Thợ', 'daily_wage': 0}
                )
                if position and emp.position != position:
                    emp.position = position
                    emp.save()

                col_idx = 3  # Cột D = index 3
                for d in dates:
                    hc_val = from_symbol(row[col_idx].value)
                    tc_raw = row[col_idx + 1].value
                    try:
                        tc_val = Decimal(str(tc_raw)) if tc_raw else Decimal('0')
                    except:
                        tc_val = Decimal('0')

                    att, _ = Attendance.objects.get_or_create(employee=emp, date=d)
                    att.regular_workday = hc_val
                    att.overtime_workday = tc_val
                    att.save()
                    col_idx += 2

                # Lương ngày - cột T (index 19)
                wage = row[19].value
                if wage:
                    try:
                        emp.daily_wage = Decimal(str(wage).replace('.', '').replace(',', ''))
                    except:
                        pass
                    emp.save()

                # Tăng/giảm - cột U (index 20)
                adj_val_raw = row[20].value
                if adj_val_raw:
                    try:
                        adj_val = Decimal(str(adj_val_raw).replace('.', '').replace(',', ''))
                    except:
                        adj_val = Decimal('0')

                    if adj_val != Decimal('0'):
                        adj, _ = Adjustment.objects.get_or_create(
                            employee=emp,
                            start_date=dates[0],
                            end_date=dates[-1]
                        )
                        adj.amount = adj_val
                        adj.save()

    return redirect(f"/?date={request.POST.get('current_date', '')}")

def delete_all_data(request):
    # Check authorization - only managers can delete all
    if not request.user.is_authenticated:
        messages.error(request, 'Bạn phải đăng nhập để thực hiện chức năng này.')
        return redirect('login:login')
    
    try:
        role = request.user.profile.role
        if role != 'manager':
            messages.error(request, 'Chỉ quản lý mới có thể xóa tất cả dữ liệu.')
            return redirect('payroll:payroll_sheet')
    except:
        messages.error(request, 'Lỗi: Hồ sơ người dùng không hợp lệ.')
        return redirect('login:login')
    
    Employee.objects.all().delete()
    messages.success(request, 'Đã xóa tất cả dữ liệu nhân viên.')
    return redirect('payroll:payroll_sheet')

def save_attendance(request):
    # Check authorization - only users and managers can save
    if not request.user.is_authenticated:
        messages.error(request, 'Bạn phải đăng nhập để thực hiện chức năng này.')
        return redirect('login:login')
    
    try:
        role = request.user.profile.role
        if role not in ['manager', 'user']:
            messages.error(request, 'Bạn không có quyền lưu dữ liệu chấm công.')
            return redirect('payroll:payroll_sheet')
    except:
        messages.error(request, 'Lỗi: Hồ sơ người dùng không hợp lệ.')
        return redirect('login:login')
    if request.method == 'POST':
        current_date_str = request.POST.get('current_date')
        try:
            target_date = datetime.datetime.strptime(current_date_str, '%Y-%m-%d').date()
        except Exception:
            target_date = timezone.now().date()

        view_type = request.POST.get('view_type', 'week')
        if view_type == 'month':
            import calendar
            first_day = target_date.replace(day=1)
            last_day = target_date.replace(day=calendar.monthrange(target_date.year, target_date.month)[1])
            dates = [first_day + datetime.timedelta(days=i) for i in range((last_day - first_day).days + 1)]
        else:
            dates = get_week_range(target_date)

        start_date, end_date = dates[0], dates[-1]
        search_query = request.POST.get('q', '').strip()
        employees = get_filtered_employees(search_query)

        for emp in employees:
            for d in dates:
                date_str = d.strftime('%Y-%m-%d')
                hc_val = parse_attendance_input(request.POST.get(f'att_{emp.id}_{date_str}_hc'))
                tc_val = parse_attendance_input(request.POST.get(f'att_{emp.id}_{date_str}_tc'))

                if hc_val == Decimal('0.0') and tc_val == Decimal('0.0'):
                    Attendance.objects.filter(employee=emp, date=d).delete()
                else:
                    att, _ = Attendance.objects.get_or_create(employee=emp, date=d)
                    att.regular_workday = hc_val
                    att.overtime_workday = tc_val
                    att.save()

            adj_name = f'adj_{emp.id}_{start_date.strftime("%Y-%m-%d")}_{end_date.strftime("%Y-%m-%d")}'
            adj_val = parse_attendance_input(request.POST.get(adj_name))
            adjustment, created = Adjustment.objects.get_or_create(
                employee=emp,
                start_date=start_date,
                end_date=end_date,
                defaults={'amount': Decimal('0.0')}
            )

            if adj_val == Decimal('0.0'):
                if not created:
                    adjustment.delete()
            else:
                adjustment.amount = adj_val
                adjustment.save()

        redirect_url = f"/?date={current_date_str}&view_type={view_type}"
        if search_query:
            redirect_url += f"&q={search_query}&search_type={request.POST.get('search_type', 'name')}"
        return redirect(redirect_url)

    return redirect('payroll:payroll_sheet')

def export_payroll_excel(dates, start_date, end_date, view_type='week'):
    wb = Workbook()
    ws = wb.active
    ws.title = "Bang Cham Cong"

    # Header Info
    ws.merge_cells('A1:E1')
    ws['A1'] = "CÔNG TY TNHH XÂY DỰNG CPT"
    ws['A1'].font = Font(bold=True, size=12)
    
    ws.merge_cells('A2:E2')
    ws['A2'] = "Địa chỉ: TP. Hồ Chí Minh"
    
    # Calculate columns count to merge header row 3 correctly
    # 3 cols (STT, Name, Job) + 2 * len(dates) + 7 cols (Totals/Actions/etc)
    total_cols_count = 3 + 2 * len(dates) + 7
    from openpyxl.utils import get_column_letter
    max_col_letter = get_column_letter(total_cols_count)
    
    ws.merge_cells(f'A3:{max_col_letter}3')
    if view_type == 'month':
        ws['A3'] = f"BẢNG CHẤM CÔNG VÀ TÍNH LƯƠNG (Tháng: {start_date.strftime('%m/%Y')})"
    else:
        ws['A3'] = f"BẢNG CHẤM CÔNG VÀ TÍNH LƯƠNG (Tuần: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')})"
    ws['A3'].font = Font(bold=True, size=14)
    ws['A3'].alignment = Alignment(horizontal='center')

    # Table Headers
    headers = ['STT', 'Họ tên', 'Nghề']
    ws.append(headers) # Row 4 placeholder
    
    # Merge for STT, Name, Job
    for col in ['A', 'B', 'C']:
        ws.merge_cells(f'{col}4:{col}5')
        ws[f'{col}4'].alignment = Alignment(horizontal='center', vertical='center')
        ws[f'{col}4'].fill = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid")

    ws['A4'], ws['B4'], ws['C4'] = 'STT', 'Họ tên', 'Nghề'
    
    # Date headers
    col_offset = 4 # Column D
    v_days = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for i, d in enumerate(dates):
        cell = ws.cell(row=4, column=col_offset)
        weekday_idx = d.weekday()
        cell.value = f"{v_days[weekday_idx]} {d.strftime('%d/%m')}"
        ws.merge_cells(start_row=4, start_column=col_offset, end_row=4, end_column=col_offset+1)
        cell.alignment = Alignment(horizontal='center')
        cell.fill = PatternFill(start_color="CFE2F3", end_color="CFE2F3", fill_type="solid")
        
        ws.cell(row=5, column=col_offset).value = "HC"
        ws.cell(row=5, column=col_offset+1).value = "TC"
        ws.cell(row=5, column=col_offset).fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        col_offset += 2

    # Result headers
    res_headers = ['Tổng HC', 'Tổng TC', 'Lương ngày', 'Tăng/Giảm', 'Tổng lãnh', 'Ký nhận', 'Ghi chú']
    for i, h in enumerate(res_headers):
        cell = ws.cell(row=4, column=col_offset + i)
        cell.value = h
        ws.merge_cells(start_row=4, start_column=col_offset + i, end_row=5, end_column=col_offset + i)
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.fill = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid")

    # Data
    employees = Employee.objects.all().order_by('name')
    row_num = 6
    border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    for idx, emp in enumerate(employees, 1):
        ws.cell(row=row_num, column=1).value = idx
        ws.cell(row=row_num, column=2).value = emp.name
        ws.cell(row=row_num, column=3).value = emp.position
        
        total_hc = Decimal('0.0')
        total_tc = Decimal('0.0')
        c_idx = 4
        for d in dates:
            att = Attendance.objects.filter(employee=emp, date=d).first()
            hc = att.regular_workday if att else Decimal('0.0')
            tc = att.overtime_workday if att else Decimal('0.0')
            ws.cell(row=row_num, column=c_idx).value = to_symbol(hc) if hc > 0 else ""
            ws.cell(row=row_num, column=c_idx+1).value = float(tc) if tc > 0 else ""
            total_hc += hc
            total_tc += tc
            c_idx += 2
            
        ws.cell(row=row_num, column=c_idx).value = float(total_hc)
        ws.cell(row=row_num, column=c_idx+1).value = float(total_tc)
        ws.cell(row=row_num, column=c_idx+2).value = float(emp.daily_wage)
        ws.cell(row=row_num, column=c_idx+2).number_format = '#,##0'
        
        adj = Adjustment.objects.filter(employee=emp, start_date=start_date, end_date=end_date).first()
        adj_val = adj.amount if adj else Decimal('0.0')
        ws.cell(row=row_num, column=c_idx+3).value = float(adj_val)
        ws.cell(row=row_num, column=c_idx+3).font = Font(color="FF0000")
        
        total_pay = (total_hc * emp.daily_wage) + (total_tc * (emp.daily_wage / Decimal('8'))) + adj_val
        ws.cell(row=row_num, column=c_idx+4).value = float(total_pay)
        ws.cell(row=row_num, column=c_idx+4).font = Font(bold=True)
        ws.cell(row=row_num, column=c_idx+4).number_format = '#,##0'
        
        row_num += 1

    # Style all cells
    for r in ws.iter_rows(min_row=4, max_row=row_num-1, min_col=1, max_col=col_offset+len(res_headers)-1):
        for cell in r:
            cell.border = border
            if not cell.alignment.horizontal:
                cell.alignment = Alignment(horizontal='center')

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    if view_type == 'month':
        response['Content-Disposition'] = f'attachment; filename=BangLuongThang_{start_date.strftime("%m_%Y")}.xlsx'
    else:
        response['Content-Disposition'] = f'attachment; filename=BangLuongTuan_{start_date}.xlsx'
    wb.save(response)
    return response


