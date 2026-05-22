from django.http import JsonResponse
from django.shortcuts import render

from base.models import Company
from employee.filters import EmployeeFilter
from employee.models import Employee
from horilla.decorators import login_required, permission_required
from django.apps import apps


@login_required
@permission_required(perm="employee.view_employee")
def employee_report(request):
    company = "all"
    selected_company = request.session.get("selected_company")
    if selected_company != "all":
        company = Company.objects.filter(id=selected_company).first()

    return render(
        request,
        "report/employee_report.html",
        {"company": company, "f": EmployeeFilter()},
    )


@login_required
@permission_required(perm="employee.view_employee")
def employee_pivot(request):
    qs = Employee.objects.all()
    filtered_qs = EmployeeFilter(request.GET, queryset=qs)
    qs = filtered_qs.qs

    include_indonesia = apps.is_installed("horilla_id")
    data = list(
        qs.values(
            "employee_first_name",
            "employee_last_name",
            "gender",
            "email",
            "phone",
            "employee_work_info__department_id__department",
            "employee_work_info__job_position_id__job_position",
            "employee_work_info__job_role_id__job_role",
            "employee_work_info__work_type_id__work_type",
            "employee_work_info__shift_id__employee_shift",
            "employee_work_info__employee_type_id__employee_type",
            "employee_work_info__reporting_manager_id__employee_first_name",
            "employee_work_info__reporting_manager_id__employee_last_name",
            "employee_work_info__company_id__company",
            "employee_work_info__date_joining",
            "employee_work_info__experience",
            "employee_bank_details__bank_name",
            "employee_bank_details__branch",
            "employee_bank_details__account_number",
            "employee_bank_details__any_other_code1",
            "employee_bank_details__any_other_code2",
            "employee_bank_details__country",
            "employee_bank_details__state",
            "employee_bank_details__city",
            *((
                [
                    "indonesia_profile__npwp",
                    "indonesia_profile__nik",
                    "indonesia_profile__bpjs_kesehatan",
                    "indonesia_profile__bpjs_ketenagakerjaan",
                ]
                if include_indonesia
                else []
            )),
        )
    )
    choice_gender = {
        "male": "Male",
        "female": "Female",
        "other": "Other",
    }

    # Transform data to match format
    data_list = [
        {
            "Name": f"{item['employee_first_name']} {item['employee_last_name']}",
            "Gender": choice_gender.get(item["gender"]),
            "Email": item["email"],
            "Phone": item["phone"],
            "Department": (
                item["employee_work_info__department_id__department"]
                if item["employee_work_info__department_id__department"]
                else "-"
            ),
            "Job Position": (
                item["employee_work_info__job_position_id__job_position"]
                if item["employee_work_info__job_position_id__job_position"]
                else "-"
            ),
            "Job Role": (
                item["employee_work_info__job_role_id__job_role"]
                if item["employee_work_info__job_role_id__job_role"]
                else "-"
            ),
            "Work Type": (
                item["employee_work_info__work_type_id__work_type"]
                if item["employee_work_info__work_type_id__work_type"]
                else "-"
            ),
            "Shift": (
                item["employee_work_info__shift_id__employee_shift"]
                if item["employee_work_info__shift_id__employee_shift"]
                else "-"
            ),
            "Employee Type": (
                item["employee_work_info__employee_type_id__employee_type"]
                if item["employee_work_info__employee_type_id__employee_type"]
                else "-"
            ),
            "Reporting Manager": (
                f"{item['employee_work_info__reporting_manager_id__employee_first_name']} {item['employee_work_info__reporting_manager_id__employee_last_name']}"
                if item["employee_work_info__reporting_manager_id__employee_first_name"]
                else "-"
            ),
            "Date of Joining": (
                item["employee_work_info__date_joining"]
                if item["employee_work_info__date_joining"]
                else "-"
            ),
            "Experience": round(float(item["employee_work_info__experience"] or 0), 2),
            "Company": item["employee_work_info__company_id__company"],
            "Bank Name": item["employee_bank_details__bank_name"] or "-",
            "Bank Branch": item["employee_bank_details__branch"] or "-",
            "Bank Account Number": item["employee_bank_details__account_number"] or "-",
            "Bank Code #1": item["employee_bank_details__any_other_code1"] or "-",
            "Bank Code #2": item["employee_bank_details__any_other_code2"] or "-",
            "Bank Country": item["employee_bank_details__country"] or "-",
            "Bank State": item["employee_bank_details__state"] or "-",
            "Bank City": item["employee_bank_details__city"] or "-",
            **(
                {
                    "NPWP": item.get("indonesia_profile__npwp") or "-",
                    "NIK (KTP/Paspor)": item.get("indonesia_profile__nik") or "-",
                    "BPJS Kesehatan": item.get("indonesia_profile__bpjs_kesehatan")
                    or "-",
                    "BPJS Ketenagakerjaan": item.get(
                        "indonesia_profile__bpjs_ketenagakerjaan"
                    )
                    or "-",
                }
                if include_indonesia
                else {}
            ),
        }
        for item in data
    ]
    return JsonResponse(data_list, safe=False)
