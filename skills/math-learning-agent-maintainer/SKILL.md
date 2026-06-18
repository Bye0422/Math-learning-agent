---
name: math-learning-agent-maintainer
description: Maintain and evolve the Math-learning-agent project. Use when working in E:\rag_agent_project or when modifying its Streamlit UI, RAG retrieval, math exam parsing, wrongbook, evaluation harness, deployment, tests, skills, or configuration.
---

# Math-learning-agent Maintainer

Use this skill for work on `E:\rag_agent_project`.

## Mandatory Workflow

1. Inspect local code before making claims or edits.
2. Avoid reading or printing real `.env` secrets.
3. Keep changes scoped to the task. Do not rewrite unrelated modules.
4. Add or update tests for service-layer behavior changes.
5. Run the quick harness before finishing:

```powershell
.\.venv\Scripts\python.exe scripts\run_harness.py --mode quick
```

For release-level changes, run:

```powershell
.\.venv\Scripts\python.exe scripts\run_harness.py --mode full
```

Use `--eval` only when API cost and runtime are acceptable.

## Project Boundaries

- `app.py`: Streamlit composition and UI glue. Make small changes; prefer extracting helpers to `state/`, `ui/`, or `controllers/`.
- `state/session_state.py`: Streamlit session defaults and reset helpers.
- `services/retrieval_service.py`: Hybrid retrieval, rule retrieval, question reference parsing.
- `services/agent_graph.py`: LangGraph workflow state and node orchestration.
- `services/wrongbook_service.py`: SQLite wrongbook persistence and PDF export.
- `evals/run_eval_v2.py`: evaluation harness and trend reporting.
- `tests/`: offline, deterministic unit tests.

## RAG Rules

- Preserve existing metadata keys unless deliberately migrating UI and tests.
- Keep original user wording available for question-number retrieval.
- Prefer service-layer improvements before UI changes.
- Any retrieval behavior change should include tests in `tests/test_retrieval_service.py` or `tests/test_retrieval_hybrid.py`.

## Wrongbook Rules

- Do not drop or recreate `wrong_questions`.
- Add SQLite columns only through idempotent migration logic.
- Keep existing export APIs compatible; add new APIs for new behavior.
- Test database changes with temporary SQLite files, never the live `data/wrongbook.db`.

## UI Rules

- The product name is `Math-learning-agent`.
- Keep feature labels practical and task-oriented.
- Avoid marketing landing pages; this is an operational learning tool.
- After UI changes, verify Streamlit startup with the harness.

## References

Read `references/project-map.md` when you need a fuller map of modules, test commands, or task ownership.
