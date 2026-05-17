import ast
import calendar
from dataclasses import dataclass


DEFAULT_CONFIG = {
    "ptkp": {
        "TK/0": 54000000,
        "TK/1": 58500000,
        "TK/2": 63000000,
        "TK/3": 67500000,
        "K/0": 58500000,
        "K/1": 63000000,
        "K/2": 67500000,
        "K/3": 72000000,
    },
    "ter_categories": {
        "A": ["TK/0", "TK/1", "K/0"],
        "B": ["TK/2", "TK/3", "K/1", "K/2"],
        "C": ["K/3"],
    },
    "ter_tables": {
        "A": [
            (5400000, 0.00),
            (5650000, 0.0025),
            (5950000, 0.0050),
            (6300000, 0.0075),
            (6750000, 0.0100),
            (7500000, 0.0125),
            (8550000, 0.0150),
            (9650000, 0.0175),
            (10050000, 0.0200),
            (10350000, 0.0225),
            (10700000, 0.0250),
            (11050000, 0.0300),
            (11600000, 0.0350),
            (12500000, 0.0400),
            (13750000, 0.0500),
            (15100000, 0.0600),
            (16950000, 0.0700),
            (19750000, 0.0800),
            (24150000, 0.0900),
            (26450000, 0.1000),
            (28000000, 0.1100),
            (30050000, 0.1200),
            (32400000, 0.1300),
            (35400000, 0.1400),
            (39100000, 0.1500),
            (43850000, 0.1600),
            (47800000, 0.1700),
            (51400000, 0.1800),
            (56300000, 0.1900),
            (62200000, 0.2000),
            (68600000, 0.2100),
            (77500000, 0.2200),
            (89000000, 0.2300),
            (103000000, 0.2400),
            (125000000, 0.2500),
            (157000000, 0.2600),
            (206000000, 0.2700),
            (337000000, 0.2800),
            (454000000, 0.2900),
            (550000000, 0.3000),
            (695000000, 0.3100),
            (910000000, 0.3200),
            (1400000000, 0.3300),
            (None, 0.3400),
        ],
        "B": [
            (6200000, 0.00),
            (6500000, 0.0025),
            (6850000, 0.0050),
            (7300000, 0.0075),
            (9200000, 0.0100),
            (10750000, 0.0150),
            (11250000, 0.0200),
            (11600000, 0.0250),
            (12600000, 0.0300),
            (13600000, 0.0400),
            (14950000, 0.0500),
            (16400000, 0.0600),
            (18450000, 0.0700),
            (21850000, 0.0800),
            (26000000, 0.0900),
            (27700000, 0.1000),
            (29350000, 0.1100),
            (31450000, 0.1200),
            (33950000, 0.1300),
            (37100000, 0.1400),
            (41100000, 0.1500),
            (45800000, 0.1600),
            (49500000, 0.1700),
            (53800000, 0.1800),
            (58500000, 0.1900),
            (64000000, 0.2000),
            (71000000, 0.2100),
            (80000000, 0.2200),
            (93000000, 0.2300),
            (109000000, 0.2400),
            (129000000, 0.2500),
            (163000000, 0.2600),
            (211000000, 0.2700),
            (374000000, 0.2800),
            (459000000, 0.2900),
            (555000000, 0.3000),
            (704000000, 0.3100),
            (957000000, 0.3200),
            (1405000000, 0.3300),
            (None, 0.3400),
        ],
        "C": [
            (6600000, 0.00),
            (6950000, 0.0025),
            (7350000, 0.0050),
            (7800000, 0.0075),
            (8850000, 0.0100),
            (9800000, 0.0125),
            (10950000, 0.0150),
            (11200000, 0.0175),
            (12050000, 0.0200),
            (12950000, 0.0300),
            (14150000, 0.0400),
            (15550000, 0.0500),
            (17050000, 0.0600),
            (19500000, 0.0700),
            (22700000, 0.0800),
            (26600000, 0.0900),
            (28100000, 0.1000),
            (30100000, 0.1100),
            (32600000, 0.1200),
            (35400000, 0.1300),
            (38900000, 0.1400),
            (43000000, 0.1500),
            (47400000, 0.1600),
            (51200000, 0.1700),
            (55800000, 0.1800),
            (60400000, 0.1900),
            (66700000, 0.2000),
            (74500000, 0.2100),
            (83200000, 0.2200),
            (95600000, 0.2300),
            (110000000, 0.2400),
            (134000000, 0.2500),
            (169000000, 0.2600),
            (221000000, 0.2700),
            (390000000, 0.2800),
            (463000000, 0.2900),
            (561000000, 0.3000),
            (709000000, 0.3100),
            (965000000, 0.3200),
            (1419000000, 0.3300),
            (None, 0.3400),
        ],
    },
    "pasal17": [
        (60000000, 0.05),
        (250000000, 0.15),
        (500000000, 0.25),
        (5000000000, 0.30),
        (None, 0.35),
    ],
    "job_expense_rate": 0.05,
    "job_expense_cap_year": 6000000,
    "rounding_pkp": 1000,
    "no_npwp_multiplier": 1.2,
}


def parse_config(code: str | None):
    if not code:
        return DEFAULT_CONFIG
    code = code.strip()
    if not code:
        return DEFAULT_CONFIG
    try:
        config = ast.literal_eval(code)
    except Exception:
        return DEFAULT_CONFIG
    if isinstance(config, dict):
        merged = dict(DEFAULT_CONFIG)
        merged.update(config)
        return merged
    return DEFAULT_CONFIG


def resolve_ter_category(ptkp_code: str, config: dict) -> str:
    categories = config.get("ter_categories", {}) or {}
    for cat, codes in categories.items():
        if ptkp_code in (codes or []):
            return cat
    return "A"


def ter_rate_for_monthly_gross(monthly_gross: float, ptkp_code: str, config: dict) -> float:
    category = resolve_ter_category(ptkp_code, config)
    table = (config.get("ter_tables", {}) or {}).get(category) or []
    value = float(monthly_gross or 0)
    for upper, rate in table:
        if upper is None or value <= float(upper):
            return float(rate)
    return 0.0


def ptkp_amount(ptkp_code: str, config: dict) -> int:
    return int((config.get("ptkp", {}) or {}).get(ptkp_code, 54000000))


def floor_to(value: float, base: int) -> int:
    if base <= 0:
        return int(value)
    v = int(value)
    return (v // base) * base


def pasal17_tax(pkp_yearly: int, config: dict) -> float:
    rates = config.get("pasal17", []) or []
    remaining = max(0, int(pkp_yearly))
    prev = 0
    tax = 0.0
    for upper, rate in rates:
        if remaining <= 0:
            break
        if upper is None:
            taxable = remaining
        else:
            taxable = min(remaining, int(upper) - prev)
        tax += taxable * float(rate)
        remaining -= taxable
        if upper is not None:
            prev = int(upper)
    return tax


@dataclass(frozen=True)
class PPh21Result:
    tax_for_period: float
    method: str


def pph21_for_period(
    *,
    income_for_period: float,
    start_date,
    end_date,
    ptkp_code: str,
    config: dict,
    ytd_gross: float,
    ytd_pretax: float,
    ytd_tax_withheld: float,
) -> PPh21Result:
    month = end_date.month
    if month != 12:
        rate = ter_rate_for_monthly_gross(income_for_period, ptkp_code, config)
        return PPh21Result(tax_for_period=float(income_for_period) * rate, method="TER")

    annual_gross = float(ytd_gross) + float(income_for_period)
    annual_pretax = float(ytd_pretax)
    job_expense = min(
        annual_gross * float(config.get("job_expense_rate", 0.05)),
        float(config.get("job_expense_cap_year", 6000000)),
    )
    net_yearly = max(0.0, annual_gross - job_expense - annual_pretax)
    pkp = max(0.0, net_yearly - float(ptkp_amount(ptkp_code, config)))
    pkp = floor_to(pkp, int(config.get("rounding_pkp", 1000)))
    annual_tax = pasal17_tax(int(pkp), config)
    tax_for_dec = float(annual_tax) - float(ytd_tax_withheld)
    if tax_for_dec < 0:
        tax_for_dec = 0.0
    return PPh21Result(tax_for_period=tax_for_dec, method="PASAL17_DEC")


def days_in_month(date_obj) -> int:
    return calendar.monthrange(date_obj.year, date_obj.month)[1]
