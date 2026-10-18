from datetime import date

import pytest

from storage import Storage


@pytest.fixture
def db(tmp_path):
    return Storage(tmp_path / "t.db")


def test_add_and_month(db):
    db.add(date(2026, 10, 1), 450.5, "Еда", "обед")
    db.add(date(2026, 10, 3), 60, "Транспорт")
    db.add(date(2026, 9, 30), 1000, "Еда")
    items = db.month(2026, 10)
    assert [e.amount for e in items] == [60, 450.5]
    assert db.by_category(2026, 10) == {"Еда": 450.5, "Транспорт": 60}


def test_filter_and_delete(db):
    a = db.add(date(2026, 10, 1), 100, "Еда")
    db.add(date(2026, 10, 1), 200, "Связь и интернет")
    assert len(db.month(2026, 10, "Еда")) == 1
    db.delete(a)
    assert db.by_category(2026, 10) == {"Связь и интернет": 200}


def test_rejects_non_positive(db):
    with pytest.raises(ValueError):
        db.add(date(2026, 10, 1), 0, "Еда")


def test_export(db, tmp_path):
    db.add(date(2026, 10, 5), 99.9, "Учёба", "книга")
    n = db.export_csv(tmp_path / "out.csv", 2026, 10)
    text = (tmp_path / "out.csv").read_text(encoding="utf-8-sig")
    assert n == 1 and "05.10.2026;99,9;Учёба;книга" in text


@pytest.mark.parametrize("amount", [float("nan"), float("inf"), float("-inf")])
def test_rejects_nan_and_inf(db, amount):
    with pytest.raises(ValueError):
        db.add(date(2026, 10, 1), amount, "Еда")
    assert db.month(2026, 10) == []
