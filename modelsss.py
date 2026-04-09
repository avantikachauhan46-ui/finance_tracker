"""
reports.py — CSV export and monthly/yearly report rendering.
"""

from __future__ import annotations
import csv
from datetime import datetime
from pathlib import Path

from .models import get_transactions, get_monthly_summary, get_yearly_summary
from .utils import (
    header, fmt_money, money_color, print_table,
    progress_bar, green, red, yellow, cyan, bold, dim, magenta
)

MONTH_NAMES = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


# ─────────────────────────────────────────────
#  Monthly report
# ─────────────────────────────────────────────

def print_monthly_report(year: str, month: str) -> None:
    s = get_monthly_summary(year, month)
    month_name = MONTH_NAMES[int(month)]
    header(f"Monthly Report — {month_name} {year}")

    # Top-line summary
    print()
    print(f"  {'Total Income':20}  {green(fmt_money(s['income'])):>20}")
    print(f"  {'Total Expenses':20}  {red(fmt_money(s['expenses'])):>20}")
    net_fmt = money_color(s['net'])
    print(f"  {'─'*44}")
    print(f"  {bold('Net Balance'):20}  {net_fmt:>20}")
    print()

    # By category
    if s["by_category"]:
        print(cyan(f"  {'Category breakdown':}"))
        print()
        rows = []
        for r in s["by_category"]:
            t_sym = green("▲") if r["type"] == "income" else red("▼")
            rows.append([
                t_sym,
                r["name"],
                r["type"].capitalize(),
                fmt_money(r["total"]),
            ])
        print_table(
            ["", "Category", "Type", "Amount"],
            rows,
            col_align=["l", "l", "l", "r"],
        )

    # Budget alerts
    if s["budget_alerts"]:
        print()
        print(cyan("  Budget status:"))
        print()
        for b in s["budget_alerts"]:
            bar = progress_bar(b["spent"], b["budget"])
            status = ""
            if b["spent"] > b["budget"]:
                status = red("  OVER BUDGET!")
            elif b["spent"] / b["budget"] >= 0.8:
                status = yellow("  Near limit")
            print(f"  {b['name']:18} {fmt_money(b['spent']):>10} / {fmt_money(b['budget'])}  {bar}{status}")


# ─────────────────────────────────────────────
#  Yearly report
# ─────────────────────────────────────────────

def print_yearly_report(year: str) -> None:
    s = get_yearly_summary(year)
    header(f"Yearly Report — {year}")

    print()
    print(f"  {'Total Income':20}  {green(fmt_money(s['income'])):>20}")
    print(f"  {'Total Expenses':20}  {red(fmt_money(s['expenses'])):>20}")
    print(f"  {'─'*44}")
    print(f"  {bold('Net Balance'):20}  {money_color(s['net']):>20}")
    print()

    if s["monthly"]:
        print(cyan("  Month-by-month breakdown:"))
        print()
        rows = []
        for m in s["monthly"]:
            net = m["income"] - m["expenses"]
            rows.append([
                MONTH_NAMES[int(m["month"])],
                fmt_money(m["income"]),
                fmt_money(m["expenses"]),
                money_color(net),
            ])
        print_table(
            ["Month", "Income", "Expenses", "Net"],
            rows,
            col_align=["l", "r", "r", "r"],
        )


# ─────────────────────────────────────────────
#  CSV export
# ─────────────────────────────────────────────

def export_csv(
    filepath: str,
    month: str | None = None,
    year: str | None = None,
) -> int:
    """Export transactions to a CSV file. Returns row count."""
    txs = get_transactions(month=month, year=year)
    path = Path(filepath).expanduser()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Date", "Type", "Category", "Amount", "Description"])
        for t in txs:
            writer.writerow([
                t.id, t.date, t.type.capitalize(),
                t.category_name, f"{t.amount:.2f}", t.description
            ])
    return len(txs)
