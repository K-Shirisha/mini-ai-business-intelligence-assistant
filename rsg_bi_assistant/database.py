import sqlite3
import pandas as pd

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS sales (
    transaction_id TEXT PRIMARY KEY,
    order_date TEXT NOT NULL,
    product TEXT NOT NULL,
    category TEXT NOT NULL,
    region TEXT NOT NULL,
    sales_channel TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity >= 0),
    unit_price REAL NOT NULL CHECK(unit_price >= 0),
    discount_amount REAL NOT NULL CHECK(discount_amount >= 0),
    status TEXT NOT NULL,
    revenue REAL NOT NULL CHECK(revenue >= 0)
)
"""

def initialize_database(db_path="sales.db"):
    with sqlite3.connect(db_path) as conn:
        conn.execute(CREATE_SQL)
        conn.commit()

def load_csv(csv_path, db_path="sales.db"):
    """Clean and load data. Returns loaded/excluded counts."""
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={
        "transaction_id": "transaction_id",
        "order_date": "order_date",
        "sales_channel": "sales_channel",
        "unit_price": "unit_price",
        "discount_amount": "discount_amount",
    })

    required = ["transaction_id", "order_date", "product", "category", "region",
                "sales_channel", "quantity", "unit_price", "discount_amount", "status"]
    df = df[required].copy()
    initial = len(df)

    # Normalize whitespace and parse dates (input is DD-MM-YYYY).
    for col in ["transaction_id", "product", "category", "region", "sales_channel", "status"]:
        df[col] = df[col].astype("string").str.strip()
    df["order_date"] = pd.to_datetime(df["order_date"], format="%d-%m-%Y", errors="coerce")
    for col in ["quantity", "unit_price", "discount_amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Invalid/missing required values and negative amounts are excluded.
    df = df.dropna(subset=required)
    df = df[
        (df["transaction_id"] != "") &
        (df["product"] != "") &
        (df["quantity"] >= 0) &
        (df["unit_price"] >= 0) &
        (df["discount_amount"] >= 0)
    ].copy()

    df["quantity"] = df["quantity"].astype(int)
    df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")
    df["revenue"] = (df["quantity"] * df["unit_price"] - df["discount_amount"]).clip(lower=0)
    df = df.drop_duplicates(subset=["transaction_id"], keep="first")

    cols = ["transaction_id", "order_date", "product", "category", "region",
            "sales_channel", "quantity", "unit_price", "discount_amount", "status", "revenue"]
    records = df[cols].values.tolist()

    with sqlite3.connect(db_path) as conn:
        conn.execute(CREATE_SQL)
        conn.execute("DELETE FROM sales")
        conn.executemany(
            """INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            records
        )
        conn.commit()

    return {"loaded": len(df), "excluded": initial - len(df)}

def query_db(sql, params=(), db_path="sales.db"):
    """Run only internal, predefined read-only analytics queries."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
