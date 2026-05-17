from django import template

from horilla_id.models import PayrollPeriodSetting

register = template.Library()


@register.simple_tag(takes_context=True)
def payroll_period_setting(context):
    request = context.get("request")
    selected_company_id = None
    if request is not None:
        selected_company_id = request.session.get("selected_company")

    if selected_company_id and selected_company_id != "all":
        setting = PayrollPeriodSetting.objects.filter(
            company_id=selected_company_id
        ).first()
        if setting:
            return setting

    setting = PayrollPeriodSetting.objects.filter(company__isnull=True).first()
    if setting:
        return setting
    return PayrollPeriodSetting(
        payroll_period_type="calendar_month",
        cutoff_day=20,
        monthly_salary_mode="prorate_by_calendar_month",
    )

