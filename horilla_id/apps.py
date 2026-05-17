from django.apps import AppConfig


class HorillaIdConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_id"

    def ready(self):
        try:
            from django.utils.translation import gettext_lazy as _

            from employee.cbv.employee_profile import EmployeeProfileView
            from horilla_id.views.employee_profile import indonesia_tab

            EmployeeProfileView.add_tab(
                tabs=[
                    {
                        "title": _("Indonesia ID"),
                        "view": indonesia_tab,
                    }
                ]
            )
        except Exception:
            return
