from django.contrib import admin

from horilla_id.models import EmployeeIndonesiaProfile, PayrollPeriodSetting


@admin.register(EmployeeIndonesiaProfile)
class EmployeeIndonesiaProfileAdmin(admin.ModelAdmin):
    list_display = ("employee", "npwp", "nik", "bpjs_kesehatan", "bpjs_ketenagakerjaan")
    search_fields = ("employee__employee_first_name", "employee__employee_last_name", "npwp", "nik")


@admin.register(PayrollPeriodSetting)
class PayrollPeriodSettingAdmin(admin.ModelAdmin):
    list_display = ("company", "payroll_period_type", "cutoff_day", "monthly_salary_mode")
