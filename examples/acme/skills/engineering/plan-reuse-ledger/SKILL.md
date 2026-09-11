---
name: workflow-plan-feature
class: workflow/plan-feature
id: "@acme/plan-reuse-ledger"
version: 1.0.0
description: Plan multi-step work by searching the existing code first, naming reuse candidates, then defining ordered steps with acceptance checks; use before implementing anything larger than one function.
---
# @acme/plan-reuse-ledger

ACME plans start with a reuse ledger.
1. Ledger: for every noun in the requirement, the existing port/service/component that handles it, or "none".
2. Every "none" is a new module with an owner and a test; every hit is reused, never copied (`aix code clones` afterwards).
3. Steps ordered by the ledger: reuse first, new modules last; each step's check named.
4. Task with `context_files` = the ledger's files.
