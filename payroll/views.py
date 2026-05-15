import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Sum
from .models import Employee, Attendance, Adjustment
from decimal import Decimal
import pandas as pd
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Side, Font, PatternFill
from django.contrib.humanize.templatetags.humanize import intcomma

def get_week_range(date):
    start = date - datetime.timedelta(days=date.weekday())
    return [start + datetime.timedelta(days=i) for i in range(7)]

def to_symbol(val):
    if val >= 1.0: return 'x'
    if val >= 0.5: return '/'
    return ''

def from_symbol(val):
    if val is None: return Decimal('0.0')
    val_str = str(val).strip().lower()
    if val_str == 'x': return Decimal('1.0')
    if val_str == '/': return Decimal('0.5')
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

def get_filtered_employees(search_query=''):
    employees = Employee.objects.all().order_by('name')
    if search_query:
        employees = employees.filter(name__icontains=search_query)
    return employees

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
    target_date = get_target_date(request)
    search_query = request.GET.get('q', '').strip()
    dates = get_week_range(target_date)
    start_date, end_date = dates[0], dates[-1]

    if request.GET.get('export') == 'excel':
        return export_payroll_excel(start_date, end_date)

    employees = get_filtered_employees(search_query)
    payroll_data = build_weekly_payroll_data(employees, dates)

    context = {
        'dates': dates,
        'start_date': start_date,
        'end_date': end_date,
        'prev_week': start_date - datetime.timedelta(days=7),
        'next_week': start_date + datetime.timedelta(days=7),
        'payroll_data': payroll_data,
        'search_query': search_query,
    }
    return render(request, 'payroll/payroll_sheet.html', context)

def payroll_statistics(request):
    target_date = get_target_date(request)
    search_query = request.GET.get('q', '').strip()
    dates = get_week_range(target_date)
    start_date, end_date = dates[0], dates[-1]

    employees = get_filtered_employees(search_query)
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

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'prev_week': start_date - datetime.timedelta(days=7),
        'next_week': start_date + datetime.timedelta(days=7),
        'search_query': search_query,
        'payroll_data': payroll_data,
        'employee_count': len(payroll_data),
        'total_hc': total_hc,
        'total_tc': total_tc,
        'total_pay': total_pay,
        'daily_totals': daily_totals,
        'chart_rows': chart_rows,
    }
    return render(request, 'payroll/payroll_statistics.html', context)

def add_employee(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        pos = request.POST.get('position')
        wage = request.POST.get('daily_wage', 0)
        Employee.objects.create(name=name, position=pos, daily_wage=wage)
    return redirect('payroll_sheet')

def edit_employee(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        emp.name = request.POST.get('name')
        emp.position = request.POST.get('position')
        emp.daily_wage = request.POST.get('daily_wage')
        emp.save()
    return redirect('payroll_sheet')

def delete_employee(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    emp.delete()
    return redirect('payroll_sheet')

def import_excel(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        from openpyxl import load_workbook
        excel_file = request.FILES['excel_file']
        wb = load_workbook(excel_file, data_only=True)
        ws = wb.active
        
        current_date_str = request.POST.get('current_date')
        if current_date_str:
            target_date = datetime.datetime.strptime(current_date_str, '%Y-%m-%d').date()
        else:
            target_date = timezone.now().date()
            
        dates = get_week_range(target_date)
        
        for row in ws.iter_rows(min_row=6):
            name = row[1].value 
            if not name: break
            
            position = row[2].value 
            emp, _ = Employee.objects.get_or_create(name=name, defaults={'position': position or 'Tho', 'daily_wage': 0})
            
            if position and emp.position != position:
                emp.position = position
                emp.save()

            col_idx = 3 
            for d in dates:
                hc_val = from_symbol(row[col_idx].value)
                tc_val = from_symbol(row[col_idx+1].value)
                
                att, _ = Attendance.objects.get_or_create(employee=emp, date=d)
                att.regular_workday = hc_val
                att.overtime_workday = tc_val
                att.save()
                col_idx += 2
                
            # Process Wage (Column T - idx 19)
            wage = row[19].value
            if wage:
                try: 
                    # Clean currency formatting (remove . or , as separators)
                    clean_wage = str(wage).replace('.', '').replace(',', '')
                    emp.daily_wage = Decimal(clean_wage)
                except: pass
                emp.save()
                
            # Process Adjustment (Column U - idx 20)
            adj_val_raw = row[20].value
            if adj_val_raw:
                try:
                    clean_adj = str(adj_val_raw).replace('.', '').replace(',', '')
                    adj_val = Decimal(clean_adj)
                except:
                    adj_val = Decimal('0')
                
                if adj_val != Decimal('0'):
                    adj, _ = Adjustment.objects.get_or_create(employee=emp, start_date=dates[0], end_date=dates[-1])
                    adj.amount = adj_val
                    adj.save()

    return redirect(f"/?date={request.POST.get('current_date', '')}")

def delete_all_data(request):
    Employee.objects.all().delete()
    return redirect('payroll_sheet')

def save_attendance(request):
    if request.method == 'POST':
        current_date_str = request.POST.get('current_date')
        target_date = datetime.datetime.strptime(current_date_str, '%Y-%m-%d').date()
        dates = get_week_range(target_date)
        
        for key, value in request.POST.items():
            if key.startswith('att_'):
                parts = key.split('_')
                emp_id = parts[1]
                date_val = parts[2]
                att_type = parts[3]
                
                emp = Employee.objects.get(id=emp_id)
                att, _ = Attendance.objects.get_or_create(employee=emp, date=date_val)
                
                val = from_symbol(value)
                if att_type == 'hc':
                    att.regular_workday = val
                else:
                    att.overtime_workday = val
                att.save()
                
            elif key.startswith('adj_'):
                parts = key.split('_')
                emp_id = parts[1]
                emp = Employee.objects.get(id=emp_id)
                adj, _ = Adjustment.objects.get_or_create(employee=emp, start_date=dates[0], end_date=dates[-1])
                try:
                    adj.amount = Decimal(value or '0')
                    adj.save()
                except: pass
                
    return redirect(f"/?date={request.POST.get('current_date', '')}")

def export_payroll_excel(start_date, end_date):
    dates = [start_date + datetime.timedelta(days=i) for i in range(7)]
    wb = Workbook()
    ws = wb.active
    ws.title = "Bang Cham Cong"

    # Header Info
    ws.merge_cells('A1:E1')
    ws['A1'] = "CÔNG TY TNHH XÂY DỰNG CPT"
    ws['A1'].font = Font(bold=True, size=12)
    
    ws.merge_cells('A2:E2')
    ws['A2'] = "Địa chỉ: TP. Hồ Chí Minh"
    
    ws.merge_cells('A3:V3')
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
        cell.value = f"{v_days[i]} {d.strftime('%d/%m')}"
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
    response['Content-Disposition'] = f'attachment; filename=BangLuong_{start_date}.xlsx'
    wb.save(response)
    return response
