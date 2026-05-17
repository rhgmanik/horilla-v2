from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _

from base.models import Company
from horilla.decorators import login_required, permission_required
from horilla_id.forms import PayrollPeriodSettingForm
from horilla_id.models import PayrollPeriodSetting


@login_required
@permission_required("payroll.view_payrollsettings")
def save_payroll_period_setting(request):
    selected_company_id = request.session.get("selected_company")
    company = None
    if selected_company_id and selected_company_id != "all":
        company = Company.objects.filter(id=selected_company_id).first()

    instance = PayrollPeriodSetting.objects.filter(company=company).first()
    if request.method == "POST":
        form = PayrollPeriodSettingForm(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.company = company
            obj.save()
            messages.success(request, _("Payroll period setting updated."))
            if request.headers.get("HX-Request"):
                return HttpResponse("")
            return redirect("general-settings")
        if request.headers.get("HX-Request"):
            return HttpResponse("", status=400)
    return redirect("general-settings")

