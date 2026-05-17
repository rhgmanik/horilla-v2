from django.urls import path

from horilla_id.views.payslip import payslip_default_dates
from horilla_id.views.payroll import save_payroll_period_setting

urlpatterns = [
    path(
        "payroll/period-setting/",
        save_payroll_period_setting,
        name="horilla-id-payroll-period-setting",
    ),
    path(
        "payroll/payslip-default-dates/",
        payslip_default_dates,
        name="horilla-id-payslip-default-dates",
    ),
]
