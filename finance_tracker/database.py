"""
cli.py — Interactive command-line interface for Finance Tracker.
"""

from __future__ import annotations
import sys
from datetime import datetime

from .database import init_db
from .models import (
    add_transaction, get_transactions, get_transaction_by_id, delete_transaction,
    update_transaction, get_categories, add_category, delete_category, update_budget,
)
from .reports import print_monthly_report, print_yearly_report, export_csv
from .utils import (
    header, prompt, prompt_float, prompt_date, prompt_choice,
    success, error, info, print_table, fmt_money, green, red,
    yellow, cyan, bold, dim, money_color, CURRENCY_SYMBOL,
)

BANNER = r"""
  ███████╗██╗███╗   ██╗ █████╗ ███╗   ██╗ ██████╗███████╗
  ██╔════╝██║████╗  ██║██╔══██╗████╗  ██║██╔════╝██╔════╝
  █████╗  ██║██╔██╗ ██║███████║██╔██╗ ██║██║     █████╗  
  ██╔══╝  ██║██║╚██╗██║██╔══██║██║╚██╗██║██║     ██╔══╝  
  ██║     ██║██║ ╚████║██║  ██║██║ ╚████║╚██████╗███████╗
  ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝╚══════╝
              T R A C K E R   v1.0
"""


# ─────────────────────────────────────────────
#  Main menu
# ─────────────────────────────────────────────

MAIN_MENU = [
    "1. Add Transaction",
    "2. View Transactions",
    "3. Edit / Delete Transaction",
    "4. Monthly Report",
    "5. Yearly Report",
    "6. Manage Categories & Budgets",
    "7. Export to CSV",
    "8. Quick Stats",
    "0. Exit",
]


def main() -> None:
    init_db()
    print(cyan(BANNER))
    while True:
        header("Main Menu")
        for item in MAIN_MENU:
            print(f"  {item}")
        choice = prompt("\nChoice").strip()
        if   choice == "1": menu_add_transaction()
        elif choice == "2": menu_view_transactions()
        elif choice == "3": menu_edit_delete()
        elif choice == "4": menu_monthly_report()
        elif choice == "5": menu_yearly_report()
        elif choice == "6": menu_categories()
        elif choice == "7": menu_export()
        elif choice == "8": menu_quick_stats()
        elif choice == "0":
            print(cyan("\n  Goodbye! 👋\n"))
            sys.exit(0)
        else:
            error("Invalid choice. Please try again.")


# ─────────────────────────────────────────────
#  Add transaction
# ─────────────────────────────────────────────

def menu_add_transaction() -> None:
    header("Add Transaction")
    print()
    tx_type = prompt_choice("Type (1=Income, 2=Expense)", ["income", "expense"])
    cats = get_categories(type_filter=tx_type)
    if not cats:
        error(f"No {tx_type} categories found. Add one first.")
        return

    print(f"\n  Select a {tx_type} category:")
    cat_names = [c.name for c in cats]
    cat_name = prompt_choice("Category", cat_names)
    cat = next(c for c in cats if c.name == cat_name)

    amount      = prompt_float(f"Amount ({CURRENCY_SYMBOL})")
    date_str    = prompt_date()
    description = prompt("Description (optional)")

    tx = add_transaction(date_str, amount, tx_type, cat.id, description)
    success(f"Transaction #{tx.id} added — {tx_type.upper()} {fmt_money(tx.amount)} [{cat.name}]")


# ─────────────────────────────────────────────
#  View transactions
# ─────────────────────────────────────────────

def menu_view_transactions() -> None:
    header("View Transactions")
    print()
    print("  Filter by:")
    print("  1. All transactions")
    print("  2. Income only")
    print("  3. Expenses only")
    print("  4. By month")
    print("  5. By year")
    print("  6. Recent 10")

    choice = prompt("Choice", "1")
    type_filter = month = year = None
    limit = None

    if choice == "2":
        type_filter = "income"
    elif choice == "3":
        type_filter = "expense"
    elif choice == "4":
        year  = prompt("Year  (YYYY)", datetime.today().strftime("%Y"))
        month = prompt("Month (MM)",   datetime.today().strftime("%m")).zfill(2)
    elif choice == "5":
        year = prompt("Year (YYYY)", datetime.today().strftime("%Y"))
    elif choice == "6":
        limit = 10

    txs = get_transactions(
        type_filter=type_filter, month=month, year=year, limit=limit
    )
    if not txs:
        info("No transactions found.")
        return

    rows = []
    for t in txs:
        sym = green("▲") if t.type == "income" else red("▼")
        rows.append([
            str(t.id),
            t.date,
            sym,
            t.category_name,
            fmt_money(t.amount),
            t.description[:30],
        ])
    print()
    print_table(
        ["ID", "Date", "", "Category", "Amount", "Description"],
        rows,
        col_align=["r", "l", "l", "l", "r", "l"],
    )
    totals = {}
    for t in txs:
        totals[t.type] = totals.get(t.type, 0) + t.amount
    print(f"\n  Showing {len(txs)} transaction(s)  |  "
          f"Income: {green(fmt_money(totals.get('income', 0)))}  "
          f"Expenses: {red(fmt_money(totals.get('expense', 0)))}")


# ─────────────────────────────────────────────
#  Edit / delete
# ─────────────────────────────────────────────

def menu_edit_delete() -> None:
    header("Edit / Delete Transaction")
    tx_id_str = prompt("Transaction ID")
    if not tx_id_str.isdigit():
        error("Invalid ID.")
        return
    tx = get_transaction_by_id(int(tx_id_str))
    if not tx:
        error(f"No transaction with ID {tx_id_str}.")
        return

    sym = green("▲") if tx.type == "income" else red("▼")
    print(f"\n  {sym} #{tx.id}  {tx.date}  [{tx.category_name}]  "
          f"{fmt_money(tx.amount)}  {dim(tx.description)}")
    print()
    print("  1. Edit")
    print("  2. Delete")
    print("  0. Cancel")
    action = prompt("Choice", "0")

    if action == "2":
        confirm = prompt("Delete this transaction? (yes/no)", "no")
        if confirm.lower() in ("yes", "y"):
            delete_transaction(tx.id)
            success(f"Transaction #{tx.id} deleted.")
        else:
            info("Cancelled.")

    elif action == "1":
        info("Leave blank to keep current value.")
        new_date   = prompt(f"Date [{tx.date}]") or tx.date
        new_amt    = prompt(f"Amount [{tx.amount}]")
        new_amt_f  = float(new_amt.replace(",", "")) if new_amt else None
        new_desc   = prompt(f"Description [{tx.description}]")

        cats = get_categories(type_filter=tx.type)
        cat_names = [c.name for c in cats]
        print(f"\n  Current category: {tx.category_name}")
        change_cat = prompt("Change category? (yes/no)", "no")
        new_cat_id = None
        if change_cat.lower() in ("yes", "y"):
            cat_name = prompt_choice("New category", cat_names)
            new_cat_id = next(c.id for c in cats if c.name == cat_name)

        update_transaction(
            tx.id,
            date_str=new_date if new_date != tx.date else None,
            amount=new_amt_f,
            category_id=new_cat_id,
            description=new_desc if new_desc else None,
        )
        success(f"Transaction #{tx.id} updated.")


# ─────────────────────────────────────────────
#  Monthly / yearly reports
# ─────────────────────────────────────────────

def menu_monthly_report() -> None:
    header("Monthly Report")
    year  = prompt("Year  (YYYY)", datetime.today().strftime("%Y"))
    month = prompt("Month (MM)",   datetime.today().strftime("%m")).zfill(2)
    print_monthly_report(year, month)


def menu_yearly_report() -> None:
    header("Yearly Report")
    year = prompt("Year (YYYY)", datetime.today().strftime("%Y"))
    print_yearly_report(year)


# ─────────────────────────────────────────────
#  Category management
# ─────────────────────────────────────────────

def menu_categories() -> None:
    header("Manage Categories & Budgets")
    print()
    print("  1. List all categories")
    print("  2. Add new category")
    print("  3. Set budget for expense category")
    print("  4. Delete category")
    print("  0. Back")
    choice = prompt("Choice", "0")

    if choice == "1":
        cats = get_categories()
        rows = []
        for c in cats:
            budget_str = fmt_money(c.budget) if c.budget else dim("—")
            rows.append([
                str(c.id),
                c.name,
                green("Income") if c.type == "income" else red("Expense"),
                budget_str,
            ])
        print()
        print_table(["ID", "Name", "Type", "Budget"], rows, col_align=["r", "l", "l", "r"])

    elif choice == "2":
        name = prompt("Category name")
        if not name:
            error("Name cannot be empty.")
            return
        tx_type = prompt_choice("Type", ["income", "expense"])
        cat = add_category(name, tx_type)
        success(f"Category '{cat.name}' ({cat.type}) added (ID {cat.id}).")

    elif choice == "3":
        cats = get_categories(type_filter="expense")
        cat_names = [c.name for c in cats]
        print()
        cat_name = prompt_choice("Category", cat_names)
        cat = next(c for c in cats if c.name == cat_name)
        budget = prompt_float(f"Monthly budget for '{cat.name}' ({CURRENCY_SYMBOL})", min_val=0)
        update_budget(cat.id, budget)
        success(f"Budget for '{cat.name}' set to {fmt_money(budget)}.")

    elif choice == "4":
        cat_id_str = prompt("Category ID to delete")
        if not cat_id_str.isdigit():
            error("Invalid ID.")
            return
        ok = delete_category(int(cat_id_str))
        if ok:
            success("Category deleted.")
        else:
            error("Cannot delete: transactions exist for this category.")


# ─────────────────────────────────────────────
#  CSV export
# ─────────────────────────────────────────────

def menu_export() -> None:
    header("Export to CSV")
    print()
    print("  1. Export all transactions")
    print("  2. Export by month")
    print("  3. Export by year")
    choice = prompt("Choice", "1")

    month = year = None
    if choice == "2":
        year  = prompt("Year  (YYYY)", datetime.today().strftime("%Y"))
        month = prompt("Month (MM)",   datetime.today().strftime("%m")).zfill(2)
    elif choice == "3":
        year = prompt("Year (YYYY)", datetime.today().strftime("%Y"))

    default_path = f"transactions{'_'+year+month if month else '_'+year if year else ''}.csv"
    filepath = prompt("Save to", default_path)

    count = export_csv(filepath, month=month, year=year)
    success(f"{count} transaction(s) exported to {filepath}")


# ─────────────────────────────────────────────
#  Quick stats
# ─────────────────────────────────────────────

def menu_quick_stats() -> None:
    from .models import get_monthly_summary
    today    = datetime.today()
    year_str = today.strftime("%Y")
    mon_str  = today.strftime("%m")
    s = get_monthly_summary(year_str, mon_str)

    header(f"Quick Stats — {today.strftime('%B %Y')}")
    print()
    print(f"  {'Income this month':28}  {green(fmt_money(s['income'])):>15}")
    print(f"  {'Expenses this month':28}  {red(fmt_money(s['expenses'])):>15}")
    print(f"  {'Net this month':28}  {money_color(s['net']):>15}")

    # Savings rate
    if s["income"] > 0:
        rate = (s["net"] / s["income"]) * 100
        bar_fn = green if rate >= 20 else (yellow if rate >= 0 else red)
        print(f"\n  {'Savings rate':28}  {bar_fn(f'{rate:.1f}%'):>15}")

    # Top expense
    expense_cats = [r for r in s["by_category"] if r["type"] == "expense"]
    if expense_cats:
        top = expense_cats[0]
        print(f"\n  {'Top expense category':28}  {red(top['name']) + '  ' + fmt_money(top['total']):>15}")

    print()
