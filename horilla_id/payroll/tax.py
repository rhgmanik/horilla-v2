from payroll.methods.payslip_calc import calculate_gross_pay, calculate_pre_tax_deduction
from payroll.models.models import Payslip

from horilla_id.payroll.pph21 import parse_config, pph21_for_period


def calculate_taxable_amount(*_args, **kwargs):
    contract = kwargs.get("contract")
    filing = kwargs.get("filing")
    if not contract or not filing or not getattr(filing, "use_py", False):
        return None

    ptkp_code = (getattr(filing, "filing_status", "") or "").strip()
    config = parse_config(getattr(filing, "python_code", None))
    if not ptkp_code:
        return None
    ptkp_table = (config.get("ptkp", {}) or {}) if isinstance(config, dict) else {}
    if ptkp_code not in ptkp_table and not (
        ptkp_code.startswith("TK/") or ptkp_code.startswith("K/")
    ):
        return None

    employee = kwargs["employee"]
    start_date = kwargs["start_date"]
    end_date = kwargs["end_date"]

    based_year = end_date.year
    ytd_payslips = Payslip.objects.filter(
        employee_id=employee,
        end_date__year=based_year,
        end_date__lt=start_date,
    )
    ytd_tax_withheld = 0.0
    ytd_gross = 0.0
    ytd_pretax = 0.0
    for ps in ytd_payslips:
        data = ps.pay_head_data or {}
        ytd_tax_withheld += float(data.get("federal_tax") or 0)
        gross_pay = float(data.get("gross_pay") or 0)
        non_taxable_allowances = sum(
            float(a.get("amount") or 0)
            for a in (data.get("allowances") or [])
            if a and not a.get("is_taxable")
        )
        ytd_gross += gross_pay - non_taxable_allowances
        for d in data.get("pretax_deductions") or []:
            if d and d.get("is_pretax"):
                ytd_pretax += float(d.get("amount") or 0)

    if "gross_pay" in kwargs:
        gross_pay_for_period = float(kwargs.get("gross_pay") or 0)
    else:
        gross_pay_for_period = float(calculate_gross_pay(**kwargs).get("gross_pay") or 0)

    allowances_data = kwargs.get("allowances") or {}
    non_taxable_allowance_total = sum(
        float(a.get("amount") or 0)
        for a in (allowances_data.get("allowances") or [])
        if a and not a.get("is_taxable")
    )
    income_for_period = gross_pay_for_period - non_taxable_allowance_total

    if end_date.month == 12:
        current_pretax_deductions = calculate_pre_tax_deduction(**kwargs)
        for d in current_pretax_deductions.get("pretax_deductions") or []:
            if d and d.get("is_pretax"):
                ytd_pretax += float(d.get("amount") or 0)

    result = pph21_for_period(
        income_for_period=income_for_period,
        start_date=start_date,
        end_date=end_date,
        ptkp_code=ptkp_code,
        config=config,
        ytd_gross=ytd_gross,
        ytd_pretax=ytd_pretax,
        ytd_tax_withheld=ytd_tax_withheld,
    )
    tax_value = float(result.tax_for_period)
    try:
        profile = contract.employee_id.indonesia_profile
        npwp = (getattr(profile, "npwp", "") or "").strip()
    except Exception:
        npwp = ""
    if not npwp:
        multiplier = float((config or {}).get("no_npwp_multiplier") or 1.2)
        tax_value *= multiplier
    return float(tax_value)
