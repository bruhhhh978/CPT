import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import Employee, Attendance, Adjustment
import pandas as pd
from django.utils import timezone
from decimal import Decimal, InvalidOperation

def get_week_range(date=None):
    if date is None:
        date = timezone.now().date()
    # Find the Monday of the week
    start = date - datetime.timedelta(days=date.weekday())
    # Generate dates for the week
    dates = [start + datetime.timedelta(days=i) for i in range(7)]
    return dates

def payroll_sheet(request):
    # Default to current week
    target_date_str = request.GET.get('date')
    if target_date_str:
        target_date = datetime.datetime.strptime(target_date_str, '%Y-%m-%d').date()
    else:
        target_date = timezone.now().date()
    
    dates = get_week_range(target_date)
    start_date = dates[0]
    end_date = dates[-1]
    
    employees = Employee.objects.all()
    payroll_data = []
    
    for emp in employees:
        emp_attendances = Attendance.objects.filter(employee=emp, date__range=(start_date, end_date))
        att_map = {att.date: att for att in emp_attendances}
        
        row = {
            'employee': emp,
            'daily_attendance': []
        }
        
        total_hc = Decimal('0.0')
        total_tc = Decimal('0.0')
        
        for d in dates:
            att = att_map.get(d)
            if att:
                # Convert numbers to symbols for display
                hc_val = att.regular_workday
                tc_val = att.overtime_workday
                
                def to_symbol(val):
                    if val == Decimal('1.0'): return 'x'
                    if val == Decimal('0.5'): return '/'
                    if val == Decimal('0'): return ''
                    return str(val).rstrip('0').rstrip('.')
                
                row['daily_attendance'].append({
                    'date': d,
                    'hc': hc_val,
                    'tc': tc_val,
                    'hc_symbol': to_symbol(hc_val),
                    'tc_symbol': to_symbol(tc_val)
                })
                total_hc += hc_val
                total_tc += tc_val
            else:
                row['daily_attendance'].append({
                    'date': d,
                    'hc': Decimal('0.0'),
                    'tc': Decimal('0.0'),
                    'hc_symbol': '',
                    'tc_symbol': ''
                })
        
        row['total_hc'] = total_hc
        row['total_tc'] = total_tc
        
        # Get adjustment
        adj = Adjustment.objects.filter(employee=emp, start_date=start_date, end_date=end_date).first()
        adj_amount = adj.amount if adj else Decimal('0')
        row['adjustment'] = adj_amount
        
        # Calculate total pay
        # Total Pay = (Total HC + Total TC) * Daily Wage + Adjustment
        # Note: In some systems, TC might have a different rate, but based on the image:
        # Tổng lãnh = (Tổng công HC + Tổng công TC) * Tiền công (1 ngày) + Tăng giảm?
        # Let's check the image row 6: 1.0 HC, 0.0 TC, 560k wage, 250k increase -> 810k. Correct.
        # Row 7: 4.0 HC, 0.0 TC, 440k wage -> 1,760k. Correct.
        row['total_pay'] = (total_hc + total_tc) * emp.daily_wage + adj_amount
        
        payroll_data.append(row)

    context = {
        'dates': dates,
        'payroll_data': payroll_data,
        'start_date': start_date,
        'end_date': end_date,
        'prev_week': start_date - datetime.timedelta(days=7),
        'next_week': start_date + datetime.timedelta(days=7),
    }
    
    if request.GET.get('export') == 'excel':
        return export_payroll_excel(context)
        
    return render(request, 'payroll/payroll_sheet.html', context)

def add_employee(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        position = request.POST.get('position')
        daily_wage = request.POST.get('daily_wage')
        if name and daily_wage:
            Employee.objects.create(
                name=name,
                position=position,
                daily_wage=Decimal(daily_wage)
            )
    return redirect('payroll_sheet')

def edit_employee(request, pk):
    emp = Employee.objects.get(pk=pk)
    if request.method == 'POST':
        emp.name = request.POST.get('name')
        emp.position = request.POST.get('position')
        emp.daily_wage = Decimal(request.POST.get('daily_wage'))
        emp.save()
    return redirect('payroll_sheet')

def delete_employee(request, pk):
    emp = Employee.objects.get(pk=pk)
    emp.delete()
    return redirect('payroll_sheet')

def save_attendance(request):
    if request.method == 'POST':
        # Data format from template: attendance_{emp_id}_{date}_{type}
        for key, value in request.POST.items():
            if key.startswith('att_'):
                parts = key.split('_')
                if len(parts) == 4:
                    _, emp_id, date_str, att_type = parts
                    try:
                        # Convert symbols back to numbers
                        val_str = value.strip().lower()
                        if val_str == 'x':
                            val = Decimal('1.0')
                        elif val_str == '/':
                            val = Decimal('0.5')
                        elif not val_str:
                            val = Decimal('0.0')
                        else:
                            val = Decimal(val_str)
                            
                        emp = Employee.objects.get(id=emp_id)
                        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                        
                        att, created = Attendance.objects.get_or_create(
                            employee=emp,
                            date=date
                        )
                        
                        if att_type == 'hc':
                            att.regular_workday = val
                        else:
                            att.overtime_workday = val
                        
                        att.save()
                    except (InvalidOperation, ValueError, Employee.DoesNotExist):
                        continue
                        
            elif key.startswith('adj_'):
                parts = key.split('_')
                if len(parts) == 4:
                    _, emp_id, start_str, end_str = parts
                    try:
                        val = Decimal(value) if value else Decimal('0')
                        emp = Employee.objects.get(id=emp_id)
                        start = datetime.datetime.strptime(start_str, '%Y-%m-%d').date()
                        end = datetime.datetime.strptime(end_str, '%Y-%m-%d').date()
                        
                        adj, created = Adjustment.objects.get_or_create(
                            employee=emp,
                            start_date=start,
                            end_date=end
                        )
                        adj.amount = val
                        adj.save()
                    except (InvalidOperation, ValueError, Employee.DoesNotExist):
                        continue

    return redirect(f"/?date={request.POST.get('current_date', '')}")

def export_payroll_excel(context):
    data = []
    headers = ['STT', 'Họ tên', 'Nghề']
    for d in context['dates']:
        headers.append(f"{d.strftime('%d/%m')} HC")
        headers.append(f"{d.strftime('%d/%m')} TC")
    headers += ['Tổng HC', 'Tổng TC', 'Lương ngày', 'Tăng/Giảm', 'Tổng lãnh']
    
    def to_symbol(val):
        if val == Decimal('1.0'): return 'x'
        if val == Decimal('0.5'): return '/'
        if val == 0 or val == Decimal('0'): return ''
        return str(val)

    for i, row in enumerate(context['payroll_data'], 1):
        emp_row = [i, row['employee'].name, row['employee'].position]
        for att in row['daily_attendance']:
            emp_row.append(to_symbol(att['hc']))
            emp_row.append(to_symbol(att['tc']))
        emp_row += [
            row['total_hc'], 
            row['total_tc'], 
            row['employee'].daily_wage, 
            row['adjustment'], 
            row['total_pay']
        ]
        data.append(emp_row)
    
    df = pd.DataFrame(data, columns=headers)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=Bang_Luong_{context["start_date"]}.xlsx'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Bảng lương')
        
    return response
