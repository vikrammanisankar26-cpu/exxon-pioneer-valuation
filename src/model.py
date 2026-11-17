"""ExxonMobil cost structure, leverage and Pioneer acquisition DCF.

All figures in US$ millions. Inputs come from data/xom_10k_financials.csv
(ExxonMobil Form 10-K) and the ASSUMPTIONS block below.
"""
import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "xom_10k_financials.csv"
YEARS = ["2022", "2023", "2024", "2025"]

# Share of each operating cost line treated as variable with sales.
VARIABLE_SHARE = {
    "crude_and_product_purchases": 1.0,
    "other_taxes_and_duties": 1.0,
    "production_and_manufacturing": 0.3,  # estimate; tested at 20% and 40%
    "selling_general_admin": 0.0,
    "depreciation_and_depletion": 0.0,
    "exploration": 0.0,
    "non_service_pension": 0.0,
}

ASSUMPTIONS = {
    "risk_free": 0.045,        # 10-yr Treasury at deal close, 3 May 2024
    "beta": 0.89,
    "equity_risk_premium": 0.05,
    "pretax_cost_of_debt": 0.04,
    "tax_rate": 0.21,
    # Book weights, 31 Dec 2025: equity 259,386 + NCI 7,240; debt 9,296 + 34,241
    "equity_weight": (259_386 + 7_240) / (259_386 + 7_240 + 9_296 + 34_241),
    "price_paid": 68_000,      # $63B shares + $5B debt assumed (10-K FY2024, Note 21)
    "start_fcff": 3_997.87,    # Pioneer 2023 FCFF proxy from its 10-K
    "synergy_ramp": [0.4, 0.7] + [1.0] * 8,
}

SCENARIOS = {
    #            FCFF multiplier, pre-tax synergies, growth yrs 1-10, terminal growth
    "Worst": dict(mult=0.70, synergies=1_000, growth=-0.02, terminal=-0.02),
    "Base":  dict(mult=1.00, synergies=2_000, growth=0.02, terminal=0.00),
    "Best":  dict(mult=1.15, synergies=3_000, growth=0.04, terminal=0.01),
}


def load_financials(path=DATA):
    with open(path, newline="") as f:
        return {row["line_item"]: {y: float(row[y]) for y in YEARS} for row in csv.DictReader(f)}


def cost_structure(fin, variable_share=VARIABLE_SHARE):
    """Contribution-margin income statement and leverage for each year."""
    out = {}
    for y in YEARS:
        sales = fin["sales"][y]
        variable = sum(fin[k][y] * s for k, s in variable_share.items())
        fixed = sum(fin[k][y] * (1 - s) for k, s in variable_share.items())
        cm = sales - variable
        op_income = cm - fixed
        other = fin["income_equity_affiliates"][y] + fin["other_income"][y]
        ebit = op_income + other
        interest = fin["interest_expense"][y]
        cm_ratio = cm / sales
        breakeven = fixed / cm_ratio
        out[y] = {
            "sales": sales,
            "variable_costs": variable,
            "contribution_margin": cm,
            "cm_ratio": cm_ratio,
            "fixed_costs": fixed,
            "operating_income": op_income,
            "other_income": other,
            "ebit": ebit,
            "ebit_margin": ebit / sales,
            "dol": cm / ebit,
            "dfl": ebit / (ebit - interest),
            "interest_coverage": ebit / interest,
            "breakeven_sales": breakeven,
            "margin_of_safety": (sales - breakeven) / sales,
            "free_cash_flow": fin["operating_cash_flow"][y] - fin["capex"][y],
            "shareholder_returns": fin["dividends"][y] + fin["buybacks"][y],
        }
    return out


def wacc(a=ASSUMPTIONS):
    ke = a["risk_free"] + a["beta"] * a["equity_risk_premium"]
    kd = a["pretax_cost_of_debt"] * (1 - a["tax_rate"])
    return a["equity_weight"] * ke + (1 - a["equity_weight"]) * kd


def cash_flows(scenario="Base", a=ASSUMPTIONS, synergy_share=1.0, terminal_synergy_share=1.0,
               rate=None, start_fcff=None):
    """Year 0-10 cash flows including terminal value at year 10."""
    s = SCENARIOS[scenario]
    r = wacc(a) if rate is None else rate
    base = (a["start_fcff"] if start_fcff is None else start_fcff) * s["mult"]
    after_tax_syn = s["synergies"] * (1 - a["tax_rate"])
    flows, standalone = [-a["price_paid"]], base
    for t in range(1, 11):
        standalone *= 1 + s["growth"]
        flows.append(standalone + after_tax_syn * a["synergy_ramp"][t - 1] * synergy_share)
    fcff10 = standalone + after_tax_syn * terminal_synergy_share * synergy_share
    tv = fcff10 * (1 + s["terminal"]) / (r - s["terminal"])
    flows[-1] += tv
    return flows, tv


def npv(rate, flows):
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(flows))


def irr(flows, lo=-0.5, hi=1.0):
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if npv(mid, flows) > 0 else (lo, mid)
    return (lo + hi) / 2


def valuation(scenario="Base", rate=None, **kw):
    r = wacc() if rate is None else rate
    flows, tv = cash_flows(scenario, rate=r, **kw)
    value = npv(r, flows)
    return {"npv": value, "irr": irr(flows), "terminal_share":
            (tv / (1 + r) ** 10) / (value + ASSUMPTIONS["price_paid"]), "flows": flows}


def breakeven_wacc(scenario="Base"):
    lo, hi = 0.05, 0.15
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if valuation(scenario, rate=mid)["npv"] > 0 else (lo, mid)
    return (lo + hi) / 2
