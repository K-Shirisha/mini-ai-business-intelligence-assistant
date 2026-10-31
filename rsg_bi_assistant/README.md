# Mini AI Business Intelligence Assistant

A small natural-language sales analytics app for the RSG Research GET assessment. The Streamlit UI accepts questions, the Python backend interprets intent, and fixed parameterized SQLite queries calculate the answer. The LLM is optional; without an API key the app uses a deterministic local intent interpreter.

## Features
- CSV data cleaning and import into SQLite
- Five requested analytics: total revenue, top product, monthly trend, top region, month comparison
- Supporting figures shown with every response
- Optional OpenAI-compatible intent classification (LLM does not write SQL)
- Read-only, predefined SQL queries; no arbitrary SQL execution
- Automated tests and error handling

## Revenue definition and data handling
Revenue = quantity × unit_price − discount_amount.
Only `Completed` transactions are included in analytics. Returned transactions are excluded.
Missing/invalid required values, invalid dates, negative quantity/prices/discounts and duplicate transaction IDs are excluded or deduplicated. A missing unit price in TXN0051 is excluded. A zero quantity record remains valid and contributes zero revenue.

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
Open the local URL printed by Streamlit.

## Optional LLM integration
Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in your environment. The model classifies a question into a strict allowed intent and month values. The app validates the result against a whitelist and executes only internal, predefined SQL. The API key is never committed to Git.

If no key is configured, local intent rules support the example questions. Disclose this accurately in the submission.

## Tests
```bash
pytest -q
```

## Architecture
```text
CSV file
  |
  v
Pandas validation / cleaning
  |
  v
SQLite sales table <---- fixed parameterized SELECT queries
  |                                ^
  |                                |
  v                                |
Python question interpreter (optional LLM intent classification; whitelist validation)
  |
  v
Streamlit interface: answer + supporting figures
```

## Known limitations
- Supports a finite set of sales question types, not arbitrary analytics questions.
- Month comparison currently expects two month names in the 2026 dataset.
- Rule-based interpretation can miss paraphrases; optional LLM intent classification improves language coverage.
- No authentication or multi-user access controls; intended as an assessment prototype.
- Dataset is small; SQLite is suitable for this prototype, not high-volume concurrent production use.

## AI tool and development note (edit to reflect your actual work)
- AI tools used: [list tools you actually used].
- How AI helped: [e.g. project planning, reviewing error messages, test idea generation].
- Problems and debugging: [describe actual issue(s) and the fix].
- One-day improvement: add broader question coverage, stronger evaluation, visualization, authentication, and deployment.

## GitHub submission
```bash
git init
git add .
git commit -m "Build mini AI BI assistant"
git branch -M main
git remote add origin <your-repository-url>
git push -u origin main
```
