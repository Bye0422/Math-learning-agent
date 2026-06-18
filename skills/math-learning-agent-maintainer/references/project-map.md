# Math-learning-agent Project Map

## Common Commands

```powershell
.\.venv\Scripts\python.exe scripts\run_harness.py --mode quick
.\.venv\Scripts\python.exe scripts\check_env.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\streamlit.exe run app.py
```

## Current Architecture

- `app.py`: Streamlit page assembly, sidebar, upload flow, chat flow, wrongbook UI.
- `state/session_state.py`: session state defaults and reset helpers.
- `services/document_loader.py`: PDF/DOCX/TXT/image loading.
- `services/vector_service.py`: generic chunk splitting and vector DB creation.
- `services/retrieval_service.py`: question reference extraction, rule retrieval, vector retrieval, hybrid retrieval.
- `services/rerank_service.py`: LLM rerank.
- `services/math_exam_service.py`: math answer JSON generation.
- `services/wrongbook_service.py`: wrongbook SQLite and PDF export.
- `evals/run_eval_v2.py`: evaluation runner and trend report.

## Work Order

1. Safety/config/deployment tasks.
2. Test and harness coverage.
3. Service-layer RAG or wrongbook changes.
4. UI integration.
5. Larger `app.py` modularization.

## Validation Expectations

Run quick harness for ordinary changes. Run full harness for UI, deployment, or release changes. Run Eval V2 only for RAG behavior changes when API use is acceptable.
