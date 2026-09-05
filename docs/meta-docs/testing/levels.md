---
id: META-TEST-LEVELS
title: Test levels
---
# Test levels

| Level | Proves | Scope & rules | Naming |
|---|---|---|---|
| **Unit** | domain rules, service orchestration, serialisers, frontend pure logic/components | No network/DB/filesystem/time. Memory adapters + fakes. One behaviour per test. Fast (< 50 ms). | `test_<function>_<scenario>_<expected>` |
| **Integration** | an adapter against its real technology; two components wired together | Real DB (container or file), real HTTP to a stub server; transactional cleanup. Includes repository contract suites and migration up/down. | `test_<adapter>_<behaviour>` |
| **Functional** | an FR end-to-end through the public API (or server-rendered UI) | Black-box: app started with `memory` or test backend; asserts on responses + persisted effects; one journey per test module. | `test_<journey>_<step>` |
| **E2E** | the deployed system through a real browser/client | Few, critical journeys; runs on a deployed env; owns no logic assertions already covered lower. | `e2e_<journey>` |
| **Contract** | `API-*` docs ⇄ implementation; event schemas ⇄ consumers | Generated from OpenAPI/schemas; provider + consumer sides. | `contract_<api-id>` |
| **Security** | a `VUL-*` mitigation holds | Negative tests: injection payloads, auth bypass, IDOR, rate limit; produced by `security-audit-*` skills. | `sec_<vul-id>` |
| **Performance** | `NFR-PERF-*` budgets | Load/benchmark with recorded baseline; fail on regression > threshold. | `perf_<nfr-id>` |
| **Accessibility** | `NFR-A11Y-*` | Automated axe-style checks per view + manual checklist. | `a11y_<view>` |

## Frontend specifics
Unit (pure functions, hooks), component (render + interaction, API client mocked at the `api/` module boundary), e2e (browser). Snapshot tests only for design-system primitives.

## Choosing the level (decision)
Can it be proven with memory adapters? → unit. Does it need the real tech? → integration. Does it cross the API boundary? → functional. Does it need a browser/deployed env? → e2e.
