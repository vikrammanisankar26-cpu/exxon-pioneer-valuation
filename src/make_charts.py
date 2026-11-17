"""Builds every chart in charts/ and writes results.json. Run: python src/make_charts.py"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import model  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "charts"
OUT.mkdir(exist_ok=True)

INK, MUTED, GRID = "#1b1f1c", "#6b726d", "#e4e1d8"
GREEN, GREEN_SOFT, RED, GOLD = "#1f5c43", "#9cc3ad", "#a8432f", "#b8892b"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": GRID,
    "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "figure.dpi": 160, "savefig.bbox": "tight", "savefig.facecolor": "white",
})


def title(ax, main, sub):
    ax.set_title(main, loc="left", fontsize=14, fontweight="bold", color=INK, pad=26)
    ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=10.5, color=MUTED)


fin = model.load_financials()
cs = model.cost_structure(fin)
years = model.YEARS

# 1. Sales vs EBIT, indexed to 2022
fig, ax = plt.subplots(figsize=(9, 4.6))
sales = np.array([cs[y]["sales"] for y in years]) / 1000
ebit = np.array([cs[y]["ebit"] for y in years]) / 1000
x = np.arange(len(years))
ax.bar(x - 0.2, sales, 0.4, color=GREEN_SOFT, label="Sales")
ax.bar(x + 0.2, ebit, 0.4, color=GREEN, label="EBIT")
for i in range(len(years)):
    ax.text(x[i] + 0.2, ebit[i] + 6, f"${ebit[i]:.1f}B", ha="center", fontsize=9.5, color=INK)
    ax.text(x[i] - 0.2, sales[i] + 6, f"${sales[i]:.0f}B", ha="center", fontsize=9.5, color=MUTED)
ax.set_xticks(x, years)
ax.set_ylabel("$ billions")
ax.legend(frameon=False, loc="upper right")
title(ax, "Sales fell 3%, EBIT fell 22% (2023 to 2025)",
      "ExxonMobil sales and EBIT, $ billions, Form 10-K")
fig.savefig(OUT / "01_sales_vs_ebit.png"); plt.close(fig)

# 2. EBIT bridge 2023 -> 2025
a, b = cs["2023"], cs["2025"]
steps = [("2023 EBIT", a["ebit"]), ("Contribution\nmargin", b["contribution_margin"] - a["contribution_margin"]),
         ("Fixed costs", -(b["fixed_costs"] - a["fixed_costs"])),
         ("Affiliate &\nother income", b["other_income"] - a["other_income"]), ("2025 EBIT", b["ebit"])]
fig, ax = plt.subplots(figsize=(9, 4.6))
run = 0
for i, (lab, v) in enumerate(steps):
    if i in (0, len(steps) - 1):
        ax.bar(i, v / 1000, color=GREEN, width=0.6); run = v
        ax.text(i, v / 1000 + 1, f"${v / 1000:.1f}B", ha="center", fontweight="bold", color=INK)
    else:
        bottom = run if v >= 0 else run + v
        ax.bar(i, abs(v) / 1000, bottom=bottom / 1000, color=GREEN_SOFT if v >= 0 else RED, width=0.6)
        ax.text(i, (max(run, run + v)) / 1000 + 1, f"{'+' if v >= 0 else '−'}${abs(v) / 1000:.1f}B",
                ha="center", color=INK)
        run += v
ax.set_xticks(range(len(steps)), [s[0] for s in steps])
ax.set_ylabel("$ billions"); ax.set_ylim(0, 62)
title(ax, "Fixed costs explain 88% of the EBIT decline",
      "EBIT bridge 2023 to 2025, $ billions, contribution-margin model")
fig.savefig(OUT / "02_ebit_bridge.png"); plt.close(fig)

# 3. Operating leverage and margin of safety
fig, ax = plt.subplots(figsize=(9, 4.6))
dol = [cs[y]["dol"] for y in years]
mos = [cs[y]["margin_of_safety"] * 100 for y in years]
ax.plot(years, dol, marker="o", color=GREEN, lw=2.5, label="Degree of operating leverage (x)")
for y, v in zip(years, dol):
    ax.annotate(f"{v:.2f}x", (y, v), textcoords="offset points", xytext=(0, 9), ha="center", color=INK)
ax.set_ylabel("DOL (x)"); ax.set_ylim(1.4, 2.8)
ax2 = ax.twinx(); ax2.grid(False)
ax2.plot(years, mos, marker="s", color=GOLD, lw=2, ls="--", label="Margin of safety (%)")
for y, v in zip(years, mos):
    ax2.annotate(f"{v:.0f}%", (y, v), textcoords="offset points", xytext=(0, -16), ha="center", color=GOLD)
ax2.set_ylim(20, 60); ax2.set_ylabel("Margin of safety (%)"); ax2.spines["right"].set_visible(True)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left")
title(ax, "Profit is getting more sensitive to sales",
      "A 10% fall in 2025 sales now cuts modeled EBIT by about 24%")
fig.savefig(OUT / "03_operating_leverage.png"); plt.close(fig)

# 4. Scenario NPVs
vals = {s: model.valuation(s) for s in model.SCENARIOS}
fig, ax = plt.subplots(figsize=(9, 4.4))
names = list(vals)
npvs = [vals[s]["npv"] / 1000 for s in names]
ax.barh(names, npvs, color=[RED if v < 0 else GREEN for v in npvs], height=0.55)
ax.axvline(0, color=INK, lw=1)
for i, s in enumerate(names):
    v = npvs[i]
    ax.text(v + (1.5 if v >= 0 else -1.5), i, f"{'+' if v >= 0 else '−'}${abs(v):.1f}B  ·  IRR {vals[s]['irr'] * 100:.1f}%",
            va="center", ha="left" if v >= 0 else "right", color=INK)
ax.set_xlim(-55, 65); ax.invert_yaxis(); ax.set_xlabel("NPV, $ billions")
title(ax, "The deal clears in the base case, not by much",
      f"Pioneer acquisition NPV by scenario at a {model.wacc() * 100:.1f}% WACC, $68B paid")
fig.savefig(OUT / "04_scenario_npv.png"); plt.close(fig)

# 5. NPV vs WACC curve
rates = np.linspace(0.06, 0.11, 101)
curve = [model.valuation("Base", rate=r)["npv"] / 1000 for r in rates]
be = model.breakeven_wacc()
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.fill_between(rates * 100, curve, 0, where=np.array(curve) >= 0, color=GREEN_SOFT, alpha=0.5)
ax.fill_between(rates * 100, curve, 0, where=np.array(curve) < 0, color=RED, alpha=0.18)
ax.plot(rates * 100, curve, color=GREEN, lw=2.5)
ax.axhline(0, color=INK, lw=1)
ax.axvline(model.wacc() * 100, color=MUTED, ls=":", lw=1.5)
ax.annotate(f"Our WACC {model.wacc() * 100:.1f}%\nNPV +${vals['Base']['npv'] / 1000:.1f}B",
            (model.wacc() * 100, vals["Base"]["npv"] / 1000), xytext=(-150, -55), textcoords="offset points",
            color=INK, arrowprops=dict(arrowstyle="-", color=MUTED))
ax.plot(be * 100, 0, "o", color=RED)
ax.annotate(f"Break-even {be * 100:.1f}%", (be * 100, 0), xytext=(10, 14), textcoords="offset points", color=RED)
ax.set_xlabel("Discount rate (WACC), %"); ax.set_ylabel("NPV, $ billions")
title(ax, "A 0.8-point rise in the discount rate wipes out the value",
      "Base-case NPV with terminal value recalculated at each rate")
fig.savefig(OUT / "05_npv_vs_wacc.png"); plt.close(fig)

# 6. Tornado: one-at-a-time sensitivities
base = vals["Base"]["npv"]
tests = {
    "WACC 7%": (model.valuation("Base", rate=0.07)["npv"],),
    "Alternative starting FCFF": (model.valuation("Base", start_fcff=3_800.33)["npv"],),
    "WACC 9%": (model.valuation("Base", rate=0.09)["npv"],),
    "No terminal synergies": (model.valuation("Base", terminal_synergy_share=0)["npv"],),
    "WACC 10%": (model.valuation("Base", rate=0.10)["npv"],),
    "No synergies at all": (model.valuation("Base", synergy_share=0)["npv"],),
}
order = sorted(tests, key=lambda k: tests[k][0] - base, reverse=True)
flips = sum(v[0] < 0 for v in tests.values())
fig, ax = plt.subplots(figsize=(9, 4.8))
for i, k in enumerate(order):
    lo = tests[k][0] - base
    ax.barh(i, lo / 1000, color=RED if lo < 0 else GREEN, height=0.55)
    ax.text(lo / 1000 + (0.4 if lo >= 0 else -0.4), i, f"NPV {'+' if base + lo >= 0 else '−'}${abs(base + lo) / 1000:.1f}B",
            va="center", ha="left" if lo >= 0 else "right", color=INK, fontsize=10)
ax.set_yticks(range(len(order)), order); ax.axvline(0, color=INK, lw=1)
ax.invert_yaxis()
ax.set_xlabel("Change in NPV vs base case, $ billions"); ax.set_xlim(-28, 20)
title(ax, f"{flips} of {len(tests)} single changes turn the NPV negative",
      "One-at-a-time sensitivity, change from the +$6.9B base case")
fig.savefig(OUT / "06_sensitivity_tornado.png"); plt.close(fig)

results = {
    "cost_structure": {y: {k: round(v, 4) for k, v in cs[y].items()} for y in years},
    "wacc": round(model.wacc(), 5),
    "scenarios": {s: {"npv_musd": round(v["npv"], 1), "irr": round(v["irr"], 4),
                      "terminal_value_share": round(v["terminal_share"], 3)} for s, v in vals.items()},
    "breakeven_wacc": round(be, 4),
    "sensitivities_npv_musd": {k: round(v[0], 1) for k, v in tests.items()},
}
(ROOT / "results.json").write_text(json.dumps(results, indent=2))
print("charts and results.json written")
