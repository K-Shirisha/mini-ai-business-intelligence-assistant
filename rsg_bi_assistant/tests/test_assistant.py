import pytest
from database import initialize_database, load_csv
from assistant import answer_question

@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "test.db")
    initialize_database(db_path)
    load_csv("data/sales_data.csv", db_path)
    return db_path

def test_total_revenue(db):
    result = answer_question("What is the total revenue?", db)
    assert result["ok"]
    assert "Total revenue" in result["answer"]

def test_top_product(db):
    result = answer_question("Which product generated the highest revenue?", db)
    assert result["ok"]
    assert result["table"][0]["product"]

def test_monthly_trend(db):
    result = answer_question("What is the monthly revenue trend?", db)
    assert result["ok"]
    assert len(result["table"]) >= 1

def test_top_region(db):
    result = answer_question("Which region generated the highest sales?", db)
    assert result["ok"]
    assert result["table"][0]["region"]

def test_month_comparison(db):
    result = answer_question("How did revenue change between January and February?", db)
    assert result["ok"]
    assert len(result["table"]) == 3

def test_unknown_question(db):
    result = answer_question("Tell me a joke", db)
    assert not result["ok"]

def test_empty_question(db):
    result = answer_question("  ", db)
    assert not result["ok"]
