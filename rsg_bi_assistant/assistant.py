import os
import re
import json
import requests
from database import query_db

ALLOWED_INTENTS = {
    "total_revenue", "top_product", "monthly_trend", "top_region",
    "month_comparison", "help"
}

def _month_names(question):
    months = {
        "january": "2026-01", "february": "2026-02", "march": "2026-03",
        "april": "2026-04", "may": "2026-05", "june": "2026-06",
        "july": "2026-07", "august": "2026-08", "september": "2026-09",
        "october": "2026-10", "november": "2026-11", "december": "2026-12",
        "jan": "2026-01", "feb": "2026-02", "mar": "2026-03",
        "apr": "2026-04", "jun": "2026-06", "jul": "2026-07",
        "aug": "2026-08", "sep": "2026-09", "sept": "2026-09",
        "oct": "2026-10", "nov": "2026-11", "dec": "2026-12",
    }
    found = []
    q = question.lower()
    for name, value in months.items():
        if re.search(r"\b" + re.escape(name) + r"\b", q) and value not in found:
            found.append(value)
    return sorted(found)

def interpret_question(question):
    """Optional LLM intent interpretation; fallback is local rule-based intent mapping.
    The LLM never generates SQL. Only whitelisted intent labels are accepted.
    """
    key = os.getenv("OPENAI_API_KEY")
    if key:
        try:
            prompt = (
                "Classify a sales analytics question. Return JSON only with keys intent and months. "
                "Allowed intents: total_revenue, top_product, monthly_trend, top_region, "
                "month_comparison, help. months must be a list of YYYY-MM values, at most 2. "
                "Do not provide SQL. Question: " + question
            )
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": "You are a strict JSON intent classifier."},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"}
                },
                timeout=12
            )
            response.raise_for_status()
            data = json.loads(response.json()["choices"][0]["message"]["content"])
            intent = data.get("intent")
            months = data.get("months", [])
            if intent in ALLOWED_INTENTS and isinstance(months, list):
                months = [m for m in months if re.fullmatch(r"2026-(0[1-9]|1[0-2])", str(m))][:2]
                return {"intent": intent, "months": months, "method": "LLM"}
        except Exception:
            pass

    q = question.lower()
    months = _month_names(q)
    if any(k in q for k in ["compare", "change between", "difference between", "between"]) and len(months) >= 2:
        intent = "month_comparison"
    elif any(k in q for k in ["monthly", "month trend", "trend"]):
        intent = "monthly_trend"
    elif any(k in q for k in ["region", "area", "territory"]):
        intent = "top_region"
    elif any(k in q for k in ["product", "item"]) and any(k in q for k in ["highest", "top", "most", "best"]):
        intent = "top_product"
    elif any(k in q for k in ["total revenue", "revenue", "sales total", "overall sales"]):
        intent = "total_revenue"
    else:
        intent = "help"
    return {"intent": intent, "months": months, "method": "local intent rules"}

def _money(value):
    return f"₹{value:,.2f}"

def answer_question(question, db_path="sales.db"):
    if not isinstance(question, str) or not question.strip():
        return {"ok": False, "answer": "Please enter a non-empty question.", "intent": "invalid"}
    parsed = interpret_question(question)
    intent, months = parsed["intent"], parsed["months"]

    if intent == "total_revenue":
        rows = query_db(
            "SELECT ROUND(SUM(revenue), 2) AS total_revenue, COUNT(*) AS transactions "
            "FROM sales WHERE lower(status) = 'completed'", db_path=db_path)
        row = rows[0]
        return {"ok": True, "intent": intent,
                "answer": f"Total revenue from completed transactions is {_money(row['total_revenue'] or 0)}.",
                "table": [{"Metric": "Completed transactions", "Value": row["transactions"]},
                          {"Metric": "Total revenue", "Value": _money(row["total_revenue"] or 0)}]}

    if intent == "top_product":
        rows = query_db(
            "SELECT product, ROUND(SUM(revenue), 2) AS revenue "
            "FROM sales WHERE lower(status)='completed' GROUP BY product "
            "ORDER BY revenue DESC LIMIT 1", db_path=db_path)
        if not rows:
            return {"ok": False, "answer": "No completed transactions were found.", "intent": intent}
        r = rows[0]
        return {"ok": True, "intent": intent,
                "answer": f"{r['product']} generated the highest revenue at {_money(r['revenue'])}.",
                "table": rows}

    if intent == "monthly_trend":
        rows = query_db(
            "SELECT substr(order_date,1,7) AS month, ROUND(SUM(revenue),2) AS revenue "
            "FROM sales WHERE lower(status)='completed' GROUP BY month ORDER BY month",
            db_path=db_path)
        return {"ok": True, "intent": intent,
                "answer": "Here is the monthly revenue trend for completed transactions.",
                "table": rows}

    if intent == "top_region":
        rows = query_db(
            "SELECT region, ROUND(SUM(revenue),2) AS revenue "
            "FROM sales WHERE lower(status)='completed' GROUP BY region "
            "ORDER BY revenue DESC LIMIT 1", db_path=db_path)
        r = rows[0]
        return {"ok": True, "intent": intent,
                "answer": f"{r['region']} generated the highest sales revenue at {_money(r['revenue'])}.",
                "table": rows}

    if intent == "month_comparison":
        if len(months) < 2:
            return {"ok": False, "intent": intent,
                    "answer": "Please name two months, for example: How did revenue change between January and February?"}
        rows = query_db(
            "SELECT substr(order_date,1,7) AS month, ROUND(SUM(revenue),2) AS revenue "
            "FROM sales WHERE lower(status)='completed' AND substr(order_date,1,7) IN (?, ?) "
            "GROUP BY month ORDER BY month", (months[0], months[1]), db_path)
        values = {r["month"]: r["revenue"] for r in rows}
        first, second = months[0], months[1]
        a, b = values.get(first, 0) or 0, values.get(second, 0) or 0
        delta = b - a
        pct = (delta / a * 100) if a else None
        direction = "increased" if delta > 0 else "decreased" if delta < 0 else "did not change"
        pct_text = f" ({pct:.2f}%)" if pct is not None else " (percentage change unavailable because the first month has zero revenue)"
        return {"ok": True, "intent": intent,
                "answer": f"Revenue {direction} by {_money(abs(delta))}{pct_text} from {first} to {second}.",
                "table": [{"Month": first, "Revenue": _money(a)},
                          {"Month": second, "Revenue": _money(b)},
                          {"Metric": "Absolute change", "Value": _money(delta)}]}

    return {"ok": False, "intent": "help",
            "answer": "I can answer total revenue, highest-revenue product, monthly trend, highest-sales region, or revenue change between two named months."}
