from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from base.models import Company
from employee.models import Employee


class EmployeeIndonesiaProfile(models.Model):
    employee = models.OneToOneField(
        Employee, on_delete=models.CASCADE, related_name="indonesia_profile"
    )
    npwp = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("NPWP"))
    nik = models.CharField(
        max_length=50, null=True, blank=True, verbose_name=_("NIK (KTP/Paspor)")
    )
    bpjs_kesehatan = models.CharField(
        max_length=50, null=True, blank=True, verbose_name=_("BPJS Kesehatan")
    )
    bpjs_ketenagakerjaan = models.CharField(
        max_length=50, null=True, blank=True, verbose_name=_("BPJS Ketenagakerjaan")
    )

    def __str__(self) -> str:
        return f"Indonesia Profile - {self.employee}"


class PayrollPeriodSetting(models.Model):
    PAYROLL_PERIOD_TYPE_CHOICES = (
        ("calendar_month", _("Calendar Month (1-last)")),
        ("custom_cutoff", _("Custom Cutoff (e.g., 21-20)")),
    )
    MONTHLY_SALARY_MODE_CHOICES = (
        ("prorate_by_calendar_month", _("Prorate by Calendar Month")),
        ("full_period_as_one_month", _("Full Period as One Payroll Month")),
    )

    company = models.OneToOneField(Company, on_delete=models.CASCADE, null=True, blank=True)
    payroll_period_type = models.CharField(
        max_length=30, choices=PAYROLL_PERIOD_TYPE_CHOICES, default="calendar_month"
    )
    cutoff_day = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text=_("Used when payroll period type is Custom Cutoff (e.g., cutoff_day=20 means 21-20)."),
    )
    monthly_salary_mode = models.CharField(
        max_length=40,
        choices=MONTHLY_SALARY_MODE_CHOICES,
        default="prorate_by_calendar_month",
        help_text=_("How to calculate monthly salary when payslip period crosses calendar months."),
    )

    def clean(self):
        if self.company is None and PayrollPeriodSetting.objects.filter(company__isnull=True).exists():
            existing = PayrollPeriodSetting.objects.filter(company__isnull=True).first()
            if existing and existing.pk != self.pk:
                raise ValidationError({"company": _("Default payroll period setting already exists.")})

    def __str__(self) -> str:
        return str(self.company or _("All company"))
