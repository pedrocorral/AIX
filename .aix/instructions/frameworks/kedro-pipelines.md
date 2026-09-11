---
id: aix/frameworks/kedro-pipelines
name: "Kedro Pipeline Standards"
description: "Use when creating or changing a Kedro project: nodes, pipelines, the pipeline registry, the data catalog, parameters, hooks, datasets, pipeline tests, Ruff or typing configuration."
applyTo: "**/pipelines/**/*.py,**/pipeline_registry.py,**/settings.py,**/hooks.py,conf/**/*.yml,conf/**/*.yaml,pyproject.toml"
optional: true
---
# Kedro pipeline standards

## Shape
- The source package declared in `[tool.kedro]` is the only import root; one modular pipeline per business purpose under `<package>/pipelines/<name>/` with `nodes.py` (pure functions) and `pipeline.py` (`create_pipeline()` assembling nodes, names, tags, namespaces).
- Nodes are typed functions of in-memory values: no catalog, session, I/O, clock or randomness inside a node; those are inputs or datasets. A node is unit-testable by calling it.
- Graph assembly lives in `pipeline.py`; the registry composes pipelines under hierarchical keys (`ingest.raw`, `features.daily`, `models.train`) and exposes `__default__`.

## Catalog and layers
- Datasets named as business artefacts (`orders_clean`, `daily_features`), layered `raw → intermediate → primary → feature → model_input → models → model_output → reporting`; every dataset declares its layer and a `metadata.owner`.
- Free (in-memory) datasets only for intermediates nobody else reads; anything reused or inspected is catalogued and versioned where reproducibility matters.
- Credentials from `conf/local/` or the environment only; `conf/base/` is committed and secret-free (`aix code security` checks).

## Repetition without duplication
- The same graph for several products, sites or targets is one `create_pipeline()` instantiated with `Pipeline(base, namespace=<group>, inputs=..., outputs=..., parameters=...)`; groups come from validated parameters; instances registered as `<phase>.<group>`.
- Parameters under `params:<domain>`, close to the pipeline that owns them; validated (pydantic or a hook) before the registry composes; no magic numbers in nodes.

## Tests and quality gates
- A unit test per node with tiny in-memory frames; a pipeline test running `SequentialRunner` on a `DataCatalog` of memory datasets for every registered pipeline; a registry test that every configured group instance builds and that namespaced datasets do not collide.
- Ruff and mypy as in the Python stack; `aix code style` limits on nodes; `aix code graph --gate` (pipelines must not import each other, only shared leaves); `kedro viz` output attached to `ARCHITECTURE.md` when the graph changes.
