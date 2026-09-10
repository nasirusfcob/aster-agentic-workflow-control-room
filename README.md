# Aster Agentic Workflow Control Room

A deterministic, synthetic-data Streamlit workshop for healthcare middle managers. Participants run, inspect, challenge, adapt, and export a safely bounded agentic workflow.

## What is real

- A typed LangGraph `StateGraph` executes with an active-session in-memory checkpointer and stable thread ID.
- Python tools—not an LLM—own access-pressure math, evidence freshness/ownership validation, policy enforcement, fault injection, and PDF generation.
- Managers change demand, capacity, baseline, source age, claimed confidence, decision priority, control posture, faults, and approval; those choices alter the graph outcome.
- OpenAI, Google Gemini, Anthropic, and xAI Grok use their native HTTPS APIs. Each selected model can be connection-tested before it receives verified synthetic state.
- LangSmith tracing activates only when configured. Trace inputs contain synthetic workflow state and never participant keys or identity.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Without `WORKSHOP_ACCESS_CODE`, local access is open. For a workshop, set it in `.streamlit/secrets.toml` or the deployment secret manager; never commit it.

To enable safe LangSmith observability, configure `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGSMITH_TRACING=true`, and `LANGSMITH_HIDE_METADATA=true` in deployment secrets.

## Test

```bash
pytest -q
```

## Deploy to Streamlit Community Cloud

Push this folder to a GitHub repository, create a Community Cloud app with `app.py` as the entrypoint, and add `WORKSHOP_ACCESS_CODE` and `INSTRUCTOR_PIN` under Advanced settings → Secrets. No participant data or generated PDF is persisted.

## Safety

All scenario data is synthetic. This app prepares only a simulated leadership packet and never connects to clinical, scheduling, outreach, staffing, or production systems.
