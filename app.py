"""Учёт расходов: десктоп-приложение на Tkinter без внешних зависимостей.

Запуск: python app.py
"""
import math
import sqlite3
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

from storage import CATEGORIES, Storage

MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
PALETTE = ["#3366CC", "#DC3912", "#FF9900", "#109618", "#990099", "#0099C6", "#DD4477", "#66AA00", "#8C8C8C"]
BG = "#F5F6F8"


def money(x: float) -> str:
    return f"{x:,.2f}".replace(",", " ").replace(".", ",") + " ₽"


class App(tk.Tk):
    def __init__(self, storage: Storage):
        super().__init__()
        self.db = storage
        today = date.today()
        self.year, self.month_num = today.year, today.month
        self.title("Учёт расходов")
        self.geometry("1040x640")
        self.minsize(900, 560)
        self.configure(bg=BG)
        self._style()
        self._build_form()
        self._build_body()
        self.refresh()

    # ---------- интерфейс ----------

    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, font=("Segoe UI", 10))
        s.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
        s.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        s.configure("Total.TLabel", font=("Segoe UI", 16, "bold"))
        s.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    def _build_form(self):
        form = ttk.LabelFrame(self, text="Новый расход", padding=10)
        form.pack(fill="x", padx=12, pady=(12, 6))

        ttk.Label(form, text="Сумма").grid(row=0, column=0, sticky="w")
        self.amount = ttk.Entry(form, width=12)
        self.amount.grid(row=1, column=0, padx=(0, 10))

        ttk.Label(form, text="Категория").grid(row=0, column=1, sticky="w")
        self.category = ttk.Combobox(form, values=CATEGORIES, state="readonly", width=18)
        self.category.current(0)
        self.category.grid(row=1, column=1, padx=(0, 10))

        ttk.Label(form, text="Дата (ДД.ММ.ГГГГ)").grid(row=0, column=2, sticky="w")
        self.day = ttk.Entry(form, width=13)
        self.day.insert(0, date.today().strftime("%d.%m.%Y"))
        self.day.grid(row=1, column=2, padx=(0, 10))

        ttk.Label(form, text="Комментарий").grid(row=0, column=3, sticky="w")
        self.note = ttk.Entry(form, width=36)
        self.note.grid(row=1, column=3, padx=(0, 10), sticky="ew")
        form.columnconfigure(3, weight=1)

        ttk.Button(form, text="Добавить расход", style="Accent.TButton", command=self.add).grid(row=1, column=4)
        self.bind("<Return>", lambda _: self.add())
        self.amount.focus()

    def _build_body(self):
        body = ttk.Frame(self, padding=(12, 6, 12, 12))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(1, weight=1)

        bar = ttk.Frame(body)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Button(bar, text="◀", width=3, command=lambda: self.shift_month(-1)).pack(side="left")
        self.month_label = ttk.Label(bar, width=16, anchor="center", font=("Segoe UI", 12, "bold"))
        self.month_label.pack(side="left", padx=6)
        ttk.Button(bar, text="▶", width=3, command=lambda: self.shift_month(1)).pack(side="left")
        ttk.Label(bar, text="   Категория:").pack(side="left")
        self.filter = ttk.Combobox(bar, values=["Все"] + CATEGORIES, state="readonly", width=18)
        self.filter.current(0)
        self.filter.bind("<<ComboboxSelected>>", lambda _: self.refresh())
        self.filter.pack(side="left", padx=6)
        ttk.Button(bar, text="Экспорт в CSV", command=self.export).pack(side="right")
        ttk.Button(bar, text="Удалить выбранное", command=self.delete).pack(side="right", padx=6)

        cols = ("day", "category", "amount", "note")
        self.tree = ttk.Treeview(body, columns=cols, show="headings", selectmode="extended")
        for col, title, width, anchor in [("day", "Дата", 90, "center"), ("category", "Категория", 140, "w"),
                                          ("amount", "Сумма", 110, "e"), ("note", "Комментарий", 240, "w")]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor=anchor)
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        scroll.grid(row=1, column=0, sticky="nse")
        self.tree.bind("<Delete>", lambda _: self.delete())

        side = ttk.Frame(body, padding=(14, 0, 0, 0))
        side.grid(row=1, column=1, sticky="nsew")
        ttk.Label(side, text="Итого за месяц").pack(anchor="w")
        self.total = ttk.Label(side, style="Total.TLabel")
        self.total.pack(anchor="w", pady=(0, 6))
        self.avg = ttk.Label(side, foreground="#555")
        self.avg.pack(anchor="w")
        self.canvas = tk.Canvas(side, width=360, height=440, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, pady=(10, 0))

    # ---------- действия ----------

    def add(self):
        try:
            amount = float(self.amount.get().replace(" ", "").replace(",", "."))
            if not math.isfinite(amount):
                raise ValueError("Сумма должна быть обычным числом, например 450,50")
            d, m, y = (int(x) for x in self.day.get().strip().split("."))
            day = date(y, m, d)
            self.db.add(day, amount, self.category.get(), self.note.get())
        except ValueError as exc:
            msg = str(exc) if "Сумма" in str(exc) else "Проверьте сумму (например, 450,50) и дату в формате ДД.ММ.ГГГГ."
            messagebox.showwarning("Не удалось добавить", msg)
            return
        except sqlite3.Error as exc:
            messagebox.showerror("Ошибка базы данных", f"Запись не сохранена: {exc}")
            return
        self.amount.delete(0, "end")
        self.note.delete(0, "end")
        self.year, self.month_num = day.year, day.month
        self.refresh()
        self.amount.focus()

    def delete(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Удаление", "Выделите строки в таблице, которые нужно удалить.")
            return
        if messagebox.askyesno("Удаление", f"Удалить записей: {len(selected)}?"):
            for iid in selected:
                self.db.delete(int(iid))
            self.refresh()

    def shift_month(self, step: int):
        m = self.month_num + step
        self.year += (m - 1) // 12
        self.month_num = (m - 1) % 12 + 1
        self.refresh()

    def export(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile=f"расходы_{self.year}_{self.month_num:02d}.csv")
        if path:
            n = self.db.export_csv(path, self.year, self.month_num)
            messagebox.showinfo("Экспорт", f"Сохранено записей: {n}\n{path}")

    # ---------- отрисовка ----------

    def refresh(self):
        self.month_label.config(text=f"{MONTHS[self.month_num - 1]} {self.year}")
        cat = None if self.filter.get() == "Все" else self.filter.get()
        items = self.db.month(self.year, self.month_num, cat)
        self.tree.delete(*self.tree.get_children())
        for e in items:
            self.tree.insert("", "end", iid=str(e.id), values=(e.day.strftime("%d.%m"), e.category, money(e.amount), e.note))
        totals = self.db.by_category(self.year, self.month_num)
        total = sum(totals.values())
        self.total.config(text=money(total))
        today = date.today()
        days = today.day if (self.year, self.month_num) == (today.year, today.month) else 30
        self.avg.config(text=f"В среднем {money(total / days)} в день" if total else "Расходов пока нет")
        self.draw_pie(totals)

    def draw_pie(self, totals: dict[str, float]):
        c = self.canvas
        c.delete("all")
        total = sum(totals.values())
        if not total:
            c.create_text(180, 120, text="Добавьте первый расход,\nчтобы увидеть диаграмму", fill="#888", justify="center")
            return
        x0, y0, size = 20, 10, 200
        start = 90.0
        for i, (cat, value) in enumerate(totals.items()):
            extent = 360 * value / total
            color = PALETTE[CATEGORIES.index(cat) % len(PALETTE)] if cat in CATEGORIES else PALETTE[-1]
            if extent >= 359.99:  # Tk не рисует сектор ровно в 360°
                c.create_oval(x0, y0, x0 + size, y0 + size, fill=color, outline=BG)
            else:
                c.create_arc(x0, y0, x0 + size, y0 + size, start=start, extent=-extent, fill=color, outline=BG, width=2)
            if extent > 25:
                mid = math.radians(start - extent / 2)
                c.create_text(x0 + size / 2 + math.cos(mid) * size * 0.32, y0 + size / 2 - math.sin(mid) * size * 0.32,
                              text=f"{value / total:.0%}", fill="white", font=("Segoe UI", 9, "bold"))
            start -= extent
            ly = y0 + size + 18 + i * 20
            c.create_rectangle(x0, ly, x0 + 12, ly + 12, fill=color, outline="")
            c.create_text(x0 + 20, ly + 6, text=f"{cat}: {money(value)}", anchor="w", font=("Segoe UI", 9))
        c.create_oval(x0 + size * 0.3, y0 + size * 0.3, x0 + size * 0.7, y0 + size * 0.7, fill=BG, outline=BG)


if __name__ == "__main__":
    App(Storage()).mainloop()
