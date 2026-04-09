"""
models.py — Data-access functions for transactions and categories.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
from .database import get_connection


# ─────────────────────────────────────────────
#  Data classes
# ─────────────────────────────────────────────

@dataclass
class Category:
    id: int
    name: str
    type: str          # 'income' | 'expense'
    budget: float


@dataclass
class Transaction:
    id: int
    date: str
    amount: float
    type: str          # 'income' | 'expense'
    category_id: int
    category_name: str
    description: str
    created_at: str


# ─────────────────────────────────────────────
#  Category operations
# ─────────────────────────────────────────────

def get_categories(type_filter: Optional[str] = None) -> list[Category]:
    sql = "SELECT * FROM categories"
    params: tuple = ()
    if type_filter:
        sql += " WHERE type = ?"
        params = (type_filter,)
    sql += " ORDER BY name"
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [Category(**dict(r)) for r in rows]


def get_category_by_id(cat_id: int) -> Optional[Category]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM categories WHERE id=?", (cat_id,)).fetchone()
    return Category(**dict(row)) if row else None


def add_category(name: str, type_: str, budget: float = 0) -> Category:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO categories (name, type, budget) VALUES (?,?,?)",
            (name.strip(), type_, budget)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM categories WHERE id=?", (cur.lastrowid,)).fetchone()
    return Category(**dict(row))


def update_budget(category_id: int, budget: float) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE categories SET budget=? WHERE id=?", (budget, category_id))
        conn.commit()


def delete_category(category_id: int) -> bool:
    """Delete a category. Returns False if transactions reference it."""
    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE category_id=?", (category_id,)
        ).fetchone()[0]
        if count > 0:
            return False
        conn.execute("DELETE FROM categories WHERE id=?", (category_id,))
        conn.commit()
    return True


# ─────────────────────────────────────────────
#  Transaction operations
# ─────────────────────────────────────────────

def _row_to_tx(row) -> Transaction:
    return Transaction(
        id=row["id"],
        date=row["date"],
        amount=row["amount"],
        type=row["type"],
        category_id=row["category_id"],
        category_name=row["category_name"],
        description=row["description"] or "",
        created_at=row["created_at"],
    )


_TX_SELECT = """
    SELECT t.id, t.date, t.amount, t.type, t.category_id,
           c.name AS category_name, t.description, t.created_at
    FROM transactions t
    JOIN categories c ON c.id = t.category_id
"""


def add_transaction(
    date_str: str,
    amount: float,
    type_: str,
    category_id: int,
    description: str = "",
) -> Transaction:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO transactions (date, amount, type, category_id, description) VALUES (?,?,?,?,?)",
            (date_str, amount, type_, category_id, description.strip()),
        )
        conn.commit()
        row = conn.execute(
            _TX_SELECT + " WHERE t.id=?", (cur.lastrowid,)
        ).fetchone()
    return _row_to_tx(row)


def get_transactions(
    type_filter: Optional[str] = None,
    category_id: Optional[int] = None,
    month: Optional[str] = None,   # "YYYY-MM"
    year: Optional[str] = None,    # "YYYY"
    limit: Optional[int] = None,
) -> list[Transaction]:
    sql = _TX_SELECT + " WHERE 1=1"
    params: list = []
    if type_filter:
        sql += " AND t.type=?"
        params.append(type_filter)
    if category_id:
        sql += " AND t.category_id=?"
        params.append(category_id)
    if month:
        sql += " AND strftime('%Y-%m', t.date)=?"
        params.append(month)
    if year:
        sql += " AND strftime('%Y', t.date)=?"
        params.append(year)
    sql += " ORDER BY t.date DESC, t.id DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_tx(r) for r in rows]


def get_transaction_by_id(tx_id: int) -> Optional[Transaction]:
    with get_connection() as conn:
        row = conn.execute(_TX_SELECT + " WHERE t.id=?", (tx_id,)).fetchone()
    return _row_to_tx(row) if row else None


def delete_transaction(tx_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM transactions WHERE id=?", (tx_id,))
        conn.commit()
    return cur.rowcount > 0


def update_transaction(
    tx_id: int,
    date_str: Optional[str] = None,
    amount: Optional[float] = None,
    category_id: Optional[int] = None,
    description: Optional[str] = None,
) -> Optional[Transaction]:
    fields, params = [], []
    if date_str is not None:
        fields.append("date=?"); params.append(date_str)
    if amount is not None:
        fields.append("amount=?"); params.append(amount)
    if category_id is not None:
        fields.append("category_id=?"); params.append(category_id)
    if description is not None:
        fields.append("description=?"); params.append(description)
    if not fields:
        return get_transaction_by_id(tx_id)
    params.append(tx_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE transactions SET {', '.join(fields)} WHERE id=?", params)
        conn.commit()
    return get_transaction_by_id(tx_id)


# ─────────────────────────────────────────────
#  Summary / report queries
# ─────────────────────────────────────────────

def get_monthly_summary(year: str, month: str) -> dict:
    """Return income, expenses, net, and per-category breakdown for a month."""
    period = f"{year}-{month}"
    with get_connection() as conn:
        totals = conn.execute("""
            SELECT type, SUM(amount) as total
            FROM transactions
            WHERE strftime('%Y-%m', date) = ?
            GROUP BY type
        """, (period,)).fetchall()

        by_cat = conn.execute("""
            SELECT c.name, t.type, SUM(t.amount) as total
            FROM transactions t JOIN categories c ON c.id=t.category_id
            WHERE strftime('%Y-%m', t.date) = ?
            GROUP BY c.id, t.type
            ORDER BY total DESC
        """, (period,)).fetchall()

        budgets = conn.execute("""
            SELECT c.name, c.budget,
                   COALESCE(SUM(t.amount),0) AS spent
            FROM categories c
            LEFT JOIN transactions t
                   ON t.category_id=c.id
                  AND strftime('%Y-%m', t.date)=?
                  AND t.type='expense'
            WHERE c.type='expense' AND c.budget > 0
            GROUP BY c.id
        """, (period,)).fetchall()

    income   = next((r["total"] for r in totals if r["type"] == "income"),  0.0)
    expenses = next((r["total"] for r in totals if r["type"] == "expense"), 0.0)
    return {
        "period": period,
        "income": income,
        "expenses": expenses,
        "net": income - expenses,
        "by_category": [dict(r) for r in by_cat],
        "budget_alerts": [dict(r) for r in budgets],
    }


def get_yearly_summary(year: str) -> dict:
    with get_connection() as conn:
        monthly = conn.execute("""
            SELECT strftime('%m', date) AS month,
                   SUM(CASE WHEN type='income'  THEN amount ELSE 0 END) AS income,
                   SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS expenses
            FROM transactions
            WHERE strftime('%Y', date) = ?
            GROUP BY month
            ORDER BY month
        """, (year,)).fetchall()

        totals = conn.execute("""
            SELECT SUM(CASE WHEN type='income'  THEN amount ELSE 0 END) AS income,
                   SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS expenses
            FROM transactions
            WHERE strftime('%Y', date) = ?
        """, (year,)).fetchone()

    return {
        "year": year,
        "income": totals["income"] or 0,
        "expenses": totals["expenses"] or 0,
        "net": (totals["income"] or 0) - (totals["expenses"] or 0),
        "monthly": [dict(r) for r in monthly],
    }
