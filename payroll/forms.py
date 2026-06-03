from django import forms
from django.core.exceptions import ValidationError
from .models import CongTrinh


class CongTrinhForm(forms.ModelForm):
    class Meta:
        model = CongTrinh
        fields = ['ten_cong_trinh', 'dia_diem', 'ngay_bat_dau', 'thoi_han_ket_thuc', 'trang_thai', 'mo_ta']
        widgets = {
            'ten_cong_trinh': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập tên dự án',
                'required': True
            }),
            'dia_diem': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập địa chỉ dự án'
            }),
            'ngay_bat_dau': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'thoi_han_ket_thuc': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'trang_thai': forms.Select(attrs={
                'class': 'form-control'
            }),
            'mo_ta': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Nhập mô tả dự án'
            })
        }
        labels = {
            'ten_cong_trinh': 'Tên dự án',
            'dia_diem': 'Địa chỉ dự án',
            'ngay_bat_dau': 'Ngày bắt đầu',
            'thoi_han_ket_thuc': 'Thời hạn kết thúc',
            'trang_thai': 'Trạng thái dự án',
            'mo_ta': 'Mô tả'
        }

    def clean(self):
        cleaned_data = super().clean()
        ngay_bat_dau = cleaned_data.get('ngay_bat_dau')
        thoi_han_ket_thuc = cleaned_data.get('thoi_han_ket_thuc')
        ten_cong_trinh = cleaned_data.get('ten_cong_trinh')

        if not ten_cong_trinh or not ten_cong_trinh.strip():
            raise ValidationError('Tên dự án không được rỗng')

        if ngay_bat_dau and thoi_han_ket_thuc:
            if ngay_bat_dau > thoi_han_ket_thuc:
                raise ValidationError('Ngày bắt đầu phải trước ngày kết thúc')

        return cleaned_data
