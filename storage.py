"""Хранилище расходов на SQLite. Не зависит от интерфейса, поэтому легко тестируется."""
import csv
import math
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

CATEGORIES = ["Еда", "Транспорт", "Жильё", "Связь и интернет", "Развлечения", "Одежда", "Здоровье", "Учёба", "Другое"]


@dataclass
class Expense:
    id: int
    day: date
    amount: float
    category: str
    note: str


class Storage:
    def __init__(self, path: str | Path = "expenses.db"):
        self.conn = sqlite3.connect(path)
        self.conn.execute("""CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL, amount REAL NOT NULL CHECK (amount > 0),
            category TEXT NOT NULL, note TEXT NOT NULL DEFAULT '')""")
        self.conn.execute("CREATE INDEX IF NOT EXISTS ix_day ON expenses(day)")
        self.conn.commit()

    def add(self, day: date, amount: float, category: str, note: str = "") -> int:
        # nan и inf проходят сравнение «> 0» не так, как ожидается, отсекаем их явно
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Сумма должна быть конечным числом больше нуля")
        cur = self.conn.execute("INSERT INTO expenses (day, amount, category, note) VALUES (?, ?, ?, ?)",
                                (day.isoformat(), round(amount, 2), category, note.strip()))
        self.conn.commit()
        return cur.lastrowid

    def delete(self, expense_id: int) -> None:
        self.conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        self.conn.commit()

    def month(self, year: int, month: int, category: str | None = None) -> list[Expense]:
        sql = "SELECT id, day, amount, category, note FROM expenses WHERE substr(day, 1, 7) = ?"
        args: list = [f"{year:04d}-{month:02d}"]
        if category:
            sql += " AND category = ?"
            args.append(category)
        rows = self.conn.execute(sql + " ORDER BY day DESC, id DESC", args).fetchall()
        return [Expense(r[0], date.fromisoformat(r[1]), r[2], r[3], r[4]) for r in rows]

    def by_category(self, year: int, month: int) -> dict[str, float]:
        rows = self.conn.execute(
            "SELECT category, SUM(amount) FROM expenses WHERE substr(day, 1, 7) = ? GROUP BY category ORDER BY 2 DESC",
            (f"{year:04d}-{month:02d}",)).fetchall()
        return {c: round(s, 2) for c, s in rows}

    def months_with_data(self) -> list[str]:
        rows = self.conn.execute("SELECT DISTINCT substr(day, 1, 7) FROM expenses ORDER BY 1 DESC").fetchall()
        return [r[0] for r in rows]

    def export_csv(self, path: str | Path, year: int, month: int) -> int:
        items = self.month(year, month)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Дата", "Сумма", "Категория", "Комментарий"])
            for e in items:
                w.writerow([e.day.strftime("%d.%m.%Y"), str(e.amount).replace(".", ","), e.category, e.note])
        return len(items)
