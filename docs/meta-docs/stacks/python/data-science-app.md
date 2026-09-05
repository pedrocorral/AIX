---
id: META-STACK-PY-DS
title: Python data-science apps
---
# Python data-science apps

## Layout additions
```
backend/app/<domain>/pipelines/     # stages as pure functions: load → clean → features → model → report
backend/app/<domain>/models/        # domain concepts: Dataset, FeatureSet, Experiment, Prediction (+ ML model wrappers as adapters)
backend/app/<domain>/adapters/{files,parquet,warehouse,mlflow}/
backend/jobs/                       # pipeline entry points (idempotent, parameterised, logged)
data/{raw,interim,processed}/       # git-ignored; data/INDEX.md documents sources, schemas, licences
notebooks/                          # exploration only; numbered; nothing imported from here
frontend/ (Streamlit/Dash/Gradio)   # dashboards = View; call services through a facade, never pandas over raw files
```

## Rules
- Notebooks are disposable: any reusable code moves to `pipelines/` with tests before a task closes.
- Every stage declares input/output schemas (pandera/pydantic) and is registered in `data/INDEX.md` lineage table.
- Reproducibility: seeds fixed, environment locked, dataset versions recorded in experiment metadata (`DM-Experiment`).
- **Heavy compute (pandas/torch-scale, training, batch scoring) never runs in a request handler.** Jobs or a separate service, always (`../../architecture/background-jobs-and-events.md`). Dashboards read precomputed results.
- Persistence: file/Parquet adapters behind the same repository ports; switching to a warehouse is an adapter swap.
- Requirements: analytical outputs are requirements too (`FR-REPORT-*` with tolerances as ACs); evals live in `TS-*`.
