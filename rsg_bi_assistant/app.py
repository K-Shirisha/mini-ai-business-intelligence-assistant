import streamlit as st
from assistant import answer_question
from database import initialize_database, load_csv

st.set_page_config(page_title="Mini AI BI Assistant", page_icon="📊", layout="wide")
DB_PATH = "sales.db"
CSV_PATH = "data/sales_data.csv"

@st.cache_resource
def setup():
    initialize_database(DB_PATH)
    return load_csv(CSV_PATH, DB_PATH)

summary = setup()

st.title("📊 Mini AI Business Intelligence Assistant")
st.caption("Ask questions about sales data. Answers are calculated from the SQLite database.")

with st.sidebar:
    st.subheader("Dataset status")
    st.write(f"Rows imported: **{summary['loaded']}**")
    st.write(f"Rows excluded: **{summary['excluded']}**")
    st.write("Revenue formula: quantity × unit price − discount")
    st.write("Only Completed transactions are included in revenue analytics.")
    st.divider()
    st.markdown("**Try asking**")
    for q in [
        "What is the total revenue?",
        "Which product generated the highest revenue?",
        "What is the monthly revenue trend?",
        "Which region generated the highest sales?",
        "How did revenue change between January and February?"
    ]:
        st.code(q)

question = st.text_input("Ask a sales question", placeholder="e.g. What is the total revenue?")
if st.button("Get answer", type="primary") and question.strip():
    with st.spinner("Analyzing sales data..."):
        result = answer_question(question, DB_PATH)
    if result["ok"]:
        st.success(result["answer"])
        if result.get("table"):
            st.subheader("Supporting figures")
            st.dataframe(result["table"], use_container_width=True, hide_index=True)
        st.caption(f"Interpretation: {result['intent']} | Source: SQLite query")
    else:
        st.warning(result["answer"])
        st.info("Try one of the example questions in the sidebar.")

st.divider()
st.subheader("Dataset preview")
import pandas as pd
df = pd.read_csv(CSV_PATH)
st.dataframe(df.head(10), use_container_width=True)
