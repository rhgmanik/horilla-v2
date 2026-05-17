"""
Custom client-specific overrides.
This file is intentionally empty by default and should NOT be tracked by Git.
"""

from .base import *

# # --- 1️⃣ Basic overrides ---
# DEBUG = False
# ALLOWED_HOSTS = ["client.example.com"]
WHITE_LABELLING = True
# TWO_FACTORS_AUTHENTICATION = True

HORILLA_TAX_CALCULATOR = "horilla_id.payroll.tax.calculate_taxable_amount"
HORILLA_PAYROLL_PERIOD_CONTEXT = "horilla_id.payroll.period.monthly_salary_context"
HORILLA_PAYSLIP_DEFAULT_DATERANGE = "horilla_id.payroll.period.default_payslip_date_range"

if not any(app == "horilla_id" or app.startswith("horilla_id.") for app in INSTALLED_APPS):
    INSTALLED_APPS.append("horilla_id.apps.HorillaIdConfig")

#if not any(app == "dynamic_fields" or app.startswith("dynamic_fields.") for app in INSTALLED_APPS):
    #INSTALLED_APPS.append("dynamic_fields.apps.DynamicFieldsConfig")

LANGUAGE_CODE = "en"
LANGUAGES = (
    ("en", "English"),
    ("id", "Bahasa Indonesia"),
)

addon_locale = join(BASE_DIR, "horilla_id", "locale")
if addon_locale not in LOCALE_PATHS:
    LOCALE_PATHS.append(addon_locale)


# # --- 2️⃣ Add extra apps ---
# # Make sure to extend, not replace
# INSTALLED_APPS += [
#     "client_portal",
#     "client_analytics",
# ]


# # --- 3️⃣ Add custom middleware ---
# MIDDLEWARE += [
#     "client_portal.middleware.ClientTrackingMiddleware",
# ]


# # --- 4️⃣ Override any other settings if needed ---
# TIME_ZONE = "Europe/Berlin"
# LANGUAGE_CODE = "de"
