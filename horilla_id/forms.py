from base.forms import ModelForm
from horilla_id.models import EmployeeIndonesiaProfile, PayrollPeriodSetting


class EmployeeIndonesiaProfileForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("npwp", "nik", "bpjs_kesehatan", "bpjs_ketenagakerjaan"):
            self.fields[name].widget.attrs.update({"class": "oh-input w-100"})

    class Meta:
        model = EmployeeIndonesiaProfile
        fields = ("npwp", "nik", "bpjs_kesehatan", "bpjs_ketenagakerjaan")


class PayrollPeriodSettingForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["payroll_period_type"].widget.attrs.update({"class": "oh-select w-100"})
        self.fields["cutoff_day"].widget.attrs.update({"class": "oh-input w-100"})
        self.fields["monthly_salary_mode"].widget.attrs.update({"class": "oh-select w-100"})

    class Meta:
        model = PayrollPeriodSetting
        fields = ("payroll_period_type", "cutoff_day", "monthly_salary_mode")
