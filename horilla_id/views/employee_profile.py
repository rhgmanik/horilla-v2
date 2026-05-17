from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from employee.models import Employee
from horilla.decorators import hx_request_required, login_required
from horilla_id.forms import EmployeeIndonesiaProfileForm
from horilla_id.models import EmployeeIndonesiaProfile


@login_required
@hx_request_required
def indonesia_tab(request, pk, **_kwargs):
    employee = Employee.objects.get(id=pk)
    can_edit = request.user == employee.employee_user_id or request.user.has_perm(
        "employee.change_employee"
    )
    instance = EmployeeIndonesiaProfile.objects.filter(employee=employee).first()
    if request.method == "POST":
        if not can_edit:
            return HttpResponse(status=403)
        form = EmployeeIndonesiaProfileForm(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.employee = employee
            obj.save()
            messages.success(request, _("Indonesia profile updated."))
            instance = obj
    form = EmployeeIndonesiaProfileForm(instance=instance)
    return render(
        request,
        "horilla_id/tabs/indonesia_tab.html",
        {"employee": employee, "form": form, "can_edit": can_edit},
    )

