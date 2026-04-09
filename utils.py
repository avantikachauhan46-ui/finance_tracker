"""
utils.py — Terminal colours, formatting helpers, and input validators.
"""

from __future__ import annotations
import os
import sys
from datetime import datetime
from typing import Optional

# ─── ANSI colour helpers ───────────────────────────────────────────────────────
_NO_COLOR = not sys.stdout.isatty() or os.environ.get("NO_COLOR")

def _c(code: str, text: str) -> str:
    return text if _NO_COLOR else f"\033[{code}m{text}\033[0m"

def green(t):   return _c("32", t)
def red(t):     return _c("31", t)
def yellow(t):  return _c("33", t)
def cyan(t):    return _c("36", t)
def bold(t):    return _c("1",  t)
def dim(t):     return _c("2",  t)
def magenta(t): return _c("35", t)

# ─── Currency / number formatting ─────────────────────────────────────────────
CURRENCY_SYMBOL = os.environ.get("FT_CURRENCY", "₹")

def fmt_money(amount: float) -> str:
    return f"{CURRENCY_SYMBOL}{amount:,.2f}"

def money_color(amount: float) -> str:
    s = fmt_money(abs(amount))
    if amount > 0:
        return green(f"+{s}")
    elif amount < 0:
        return red(f"-{s}")
    return s

# ─── Table printer ────────────────────────────────────────────────────────────
def print_table(headers: list[str], rows: list[list], col_align: Optional[list[str]] = None) -> None:
    """Print a pretty fixed-width table to stdout."""
    widths = [len(h) for h in headers]
    # measure raw (no-ANSI) widths
    def raw(s: str) -> str:
        import re
        return re.sub(r"\033\[[0-9;]*m", "", str(s))

    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(raw(str(cell))))

    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    def fmt_row(cells, header=False):
        parts = []
        for i, cell in enumerate(cells):
            align = "<" if not col_align or col_align[i] == "l" else ">"
            r = raw(str(cell))
            pad = widths[i] - len(r)
            padded = (" " + str(cell) + " " * (pad + 1)) if align == "<" else (" " * (pad + 1) + str(cell) + " ")
            parts.append(padded)
        return "|" + "|".join(parts) + "|"

    print(sep)
    print(fmt_row(headers, header=True))
    print(sep)
    for row in rows:
        print(fmt_row(row))
    print(sep)

# ─── Progress bar ─────────────────────────────────────────────────────────────
def progress_bar(used: float, total: float, width: int = 20) -> str:
    if total <= 0:
        return dim("[" + "─" * width + "]")
    pct = min(used / total, 1.0)
    filled = int(pct * width)
    bar = "█" * filled + "░" * (width - filled)
    color_fn = red if pct >= 1 else (yellow if pct >= 0.8 else green)
    return color_fn(f"[{bar}]") + f" {pct*100:.0f}%"

# ─── Input helpers ────────────────────────────────────────────────────────────
def prompt(msg: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"  {msg}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise
    return val or default


def prompt_float(msg: str, min_val: float = 0.01) -> float:
    while True:
        raw = prompt(msg)
        try:
            val = float(raw.replace(",", ""))
            if val < min_val:
                print(red(f"  Value must be ≥ {min_val}"))
                continue
            return val
        except ValueError:
            print(red("  Please enter a valid number."))


def prompt_date(msg: str = "Date (YYYY-MM-DD)", default: Optional[str] = None) -> str:
    if default is None:
        default = datetime.today().strftime("%Y-%m-%d")
    while True:
        raw = prompt(msg, default)
        try:
            datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            print(red("  Invalid date. Use YYYY-MM-DD format."))


def prompt_choice(msg: str, choices: list[str]) -> str:
    """Ask user to pick from a numbered list; return chosen value."""
    for i, ch in enumerate(choices, 1):
        print(f"  {dim(str(i) + '.')} {ch}")
    while True:
        raw = prompt(msg)
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1]
        # allow typing the name directly
        matches = [c for c in choices if c.lower().startswith(raw.lower())]
        if len(matches) == 1:
            return matches[0]
        print(red(f"  Please enter a number between 1 and {len(choices)}."))

# ─── Section header ───────────────────────────────────────────────────────────
def header(title: str) -> None:
    w = 54
    print()
    print(cyan("─" * w))
    print(cyan("  ") + bold(title))
    print(cyan("─" * w))

def success(msg: str) -> None:
    print(green(f"\n  ✔  {msg}"))

def error(msg: str) -> None:
    print(red(f"\n  ✘  {msg}"))

def info(msg: str) -> None:
    print(cyan(f"\n  ℹ  {msg}"))
