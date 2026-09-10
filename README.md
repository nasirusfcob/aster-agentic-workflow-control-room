# Aster Agentic Workflow Control Room

A deterministic, synthetic-data Streamlit workshop for healthcare middle managers. Participants run, inspect, challenge, adapt, and export a safely bounded agentic workflow.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Without `WORKSHOP_ACCESS_CODE`, local access is open. For a workshop, set it in `.streamlit/secrets.toml` or the deployment secret manager; never commit it.

## Test

```bash
pytest -q
```

## Deploy to Streamlit Community Cloud

Push this folder to a GitHub repository, create a Community Cloud app with `app.py` as the entrypoint, and add `WORKSHOP_ACCESS_CODE` and `INSTRUCTOR_PIN` under Advanced settings → Secrets. No participant data or generated PDF is persisted.

## Safety

All scenario data is synthetic. This app prepares only a simulated leadership packet and never connects to clinical, scheduling, outreach, staffing, or production systems.
