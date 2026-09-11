---
id: acme/dagster-pipelines
name: "Dagster Pipeline Standards"
description: "Use when creating or changing a Dagster asset, job, resource, schedule, sensor, partition or pipeline test in an ACME data repository."
applyTo: "**/assets/**/*.py,**/definitions.py,**/resources/**/*.py,**/schedules/**/*.py,dagster.yaml,pyproject.toml"
---
# Dagster pipeline standards
- One asset per business artefact; asset names are nouns (`daily_demand`), functions are typed and pure: I/O through resources, never inside the asset body.
- Group assets by domain module `assets/<domain>/`; a `definitions.py` per repository composes them; no cross-domain import except through declared upstream assets.
- Partitions for time and for groups (site, product) instead of loops; one asset definition instantiated per partition key.
- Parameters in config schemas, validated at load; no magic numbers in assets.
- Tests: `materialize` in memory with fake resources for every asset; a schedule/sensor test per definition; `aix code style` limits apply to asset functions.
