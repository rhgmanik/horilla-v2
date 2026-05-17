import calendar
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from horilla_id.models import PayrollPeriodSetting


def get_payroll_period_setting_for_company(company):
    if company is not None:
        setting = PayrollPeriodSetting.objects.filter(company=company).first()
        if setting:
            return setting
    return PayrollPeriodSetting.objects.filter(company__isnull=True).first()


def get_payroll_period_setting_for_employee(employee):
    company = None
    try:
        company = employee.employee_work_info.company_id
    except Exception:
        company = None
    if company is not None:
        setting = PayrollPeriodSetting.objects.filter(company=company).first()
        if setting:
            return setting
    return PayrollPeriodSetting.objects.filter(company__isnull=True).first()


def resolve_standard_payroll_period(*, any_date, payroll_period_type, cutoff_day):
    if payroll_period_type == "custom_cutoff":
        cutoff_day = int(cutoff_day or 20)
        if any_date.day <= cutoff_day:
            period_end = date(
                any_date.year,
                any_date.month,
                min(cutoff_day, calendar.monthrange(any_date.year, any_date.month)[1]),
            )
            prev = period_end - relativedelta(months=1)
            prev_cutoff = date(
                prev.year,
                prev.month,
                min(cutoff_day, calendar.monthrange(prev.year, prev.month)[1]),
            )
            period_start = prev_cutoff + timedelta(days=1)
            return {"start_date": period_start, "end_date": period_end}

        current_cutoff = date(
            any_date.year,
            any_date.month,
            min(cutoff_day, calendar.monthrange(any_date.year, any_date.month)[1]),
        )
        period_start = current_cutoff + timedelta(days=1)
        nxt = current_cutoff + relativedelta(months=1)
        period_end = date(
            nxt.year,
            nxt.month,
            min(cutoff_day, calendar.monthrange(nxt.year, nxt.month)[1]),
        )
        return {"start_date": period_start, "end_date": period_end}

    last_day = calendar.monthrange(any_date.year, any_date.month)[1]
    return {
        "start_date": date(any_date.year, any_date.month, 1),
        "end_date": date(any_date.year, any_date.month, last_day),
    }


def resolve_last_closed_payroll_period(*, any_date, payroll_period_type, cutoff_day):
    if payroll_period_type == "custom_cutoff":
        cutoff_day = int(cutoff_day or 20)
        current_cutoff = date(
            any_date.year,
            any_date.month,
            min(cutoff_day, calendar.monthrange(any_date.year, any_date.month)[1]),
        )
        if any_date.day <= cutoff_day:
            last_end = current_cutoff - relativedelta(months=1)
        else:
            last_end = current_cutoff
        last_end = date(
            last_end.year,
            last_end.month,
            min(cutoff_day, calendar.monthrange(last_end.year, last_end.month)[1]),
        )
        prev_end = last_end - relativedelta(months=1)
        prev_end = date(
            prev_end.year,
            prev_end.month,
            min(cutoff_day, calendar.monthrange(prev_end.year, prev_end.month)[1]),
        )
        return {"start_date": prev_end + timedelta(days=1), "end_date": last_end}

    prev_month = any_date.replace(day=1) - timedelta(days=1)
    last_day = calendar.monthrange(prev_month.year, prev_month.month)[1]
    return {
        "start_date": date(prev_month.year, prev_month.month, 1),
        "end_date": date(prev_month.year, prev_month.month, last_day),
    }


def monthly_salary_context(*, employee, start_date, end_date, **_kwargs):
    setting = get_payroll_period_setting_for_employee(employee)
    payroll_period_type = (
        getattr(setting, "payroll_period_type", "calendar_month")
        if setting
        else "calendar_month"
    )
    cutoff_day = getattr(setting, "cutoff_day", 20) if setting else 20
    monthly_salary_mode = (
        getattr(setting, "monthly_salary_mode", "prorate_by_calendar_month")
        if setting
        else "prorate_by_calendar_month"
    )
    standard_period = resolve_standard_payroll_period(
        any_date=end_date,
        payroll_period_type=payroll_period_type,
        cutoff_day=cutoff_day,
    )
    return {
        "payroll_period_type": payroll_period_type,
        "cutoff_day": cutoff_day,
        "monthly_salary_mode": monthly_salary_mode,
        "standard_period": standard_period,
    }


def default_payslip_date_range(*, request=None):
    company = None
    if request is not None:
        selected_company_id = request.session.get("selected_company")
        if selected_company_id and selected_company_id != "all":
            try:
                company = int(selected_company_id)
            except Exception:
                company = None
    setting = None
    if company is not None:
        setting = PayrollPeriodSetting.objects.filter(company_id=company).first()
    setting = setting or PayrollPeriodSetting.objects.filter(company__isnull=True).first()

    payroll_period_type = (
        getattr(setting, "payroll_period_type", "calendar_month")
        if setting
        else "calendar_month"
    )
    cutoff_day = getattr(setting, "cutoff_day", 20) if setting else 20
    today = date.today()
    return resolve_last_closed_payroll_period(
        any_date=today, payroll_period_type=payroll_period_type, cutoff_day=cutoff_day
    )
