from django.shortcuts import render

from horilla.decorators import hx_request_required, login_required
from horilla_id.payroll.period import default_payslip_date_range


@login_required
@hx_request_required
def payslip_default_dates(request):
    data = default_payslip_date_range(request=request)
    return render(
        request,
        "horilla_id/payroll/payslip_date_fields.html",
        {"start_date": data["start_date"], "end_date": data["end_date"]},
    )

