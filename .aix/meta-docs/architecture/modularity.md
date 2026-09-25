---
id: META-ARCH-MODULARITY
title: Modularity — the shape of the dependency graph
read_when: Designing anything, adding a module, adding an import between modules, or reviewing a diff that changes who depends on whom.
---
# Modularity

Picture the code as a graph: nodes are modules (files, classes, functions), edges are dependencies (imports, calls).
**The fewer edges the better, and the graph must be acyclic and layered.** Two rules follow, and every other
architecture doc in this folder is a special case of them.

## The name and its parts
**Modularity** is the term used in research (Baldwin & Clark, *Design Rules*, 2000), measured on a Design Structure
Matrix by *propagation cost*. Its parts, each with its own literature: *separation of concerns* (Dijkstra, 1974)
and *information hiding* (Parnas, 1972) — one job per node; *low coupling, high cohesion* (Constantine, 1974) —
isolation between nodes; the *Acyclic Dependencies Principle* and *Stable Dependencies Principle* (Martin) and
*levelization* (Lakos) — the graph shape. Precisely: **modularity with acyclic, stable dependencies**.

## The two rules
1. **One job per node** (separation of concerns). Each node does one thing and hides one design decision. If describing a module needs "and",
   split it. (`layering.md`, `mvc.md` and the persistence ports are where this lands in practice.)
2. **Low coupling.** A node knows as little as possible about the others. Edges point one way only, from the
   specific toward the stable, and there are no cycles. Nothing reaches sideways into a sibling domain or upward
   into whoever calls it.

## Reuse: leaves are a bonus, hubs are a cost
Reusing a node is **not** duplication and it does **not** raise coupling in a harmful way, provided the node is a **leaf**:
pure, with a fixed contract, depending on nothing above it (pure functions, higher-order functions, value types,
parsers, formatters). Many branches may point at a leaf; that fan-in is free, and reusing leaves makes the graph
larger without making it more tangled. Prefer that over copying.

What must never be shared is a **hub**: a node that is widely depended on *and* itself reaches into state,
configuration, I/O or a domain. Every change to a hub propagates to all its dependents. Rule of thumb:
**high fan-in ⇒ zero fan-out** (except to other leaves).

| Node | Fan-in | Fan-out | Verdict |
|---|---|---|---|
| `money.round_half_even()` | high | 0 | leaf — reuse freely |
| `map_result(fn, ...)` higher-order helper | high | 0 | leaf — reuse freely |
| `orders.service.place_order()` | low (its controller) | downward only | fine |
| `common/utils.py` importing settings, db, logger | high | high | **hub — split it** |
| `billing` importing `orders` and `orders` importing `billing` | — | — | **cycle — forbidden** |

## Checks (deterministic first, then judgement)
- **No cycles** at any granularity: package, module, class. A cycle means two nodes are one node in disguise;
  merge them or extract the shared part into a leaf.
- **Direction**: edges go controller → service → repository port → model, and domain → shared leaves. Never
  domain → domain sideways (go through an event or a service in the calling layer), never leaf → anything.
- **Fan-out per node** small (a module importing more than ~7 project modules is doing too much).
- **Fan-in only on leaves**: list the top-N most-imported modules; each must have no upward dependency.
- **Propagation**: for a change in node X, the set of nodes that can be affected is X's dependents. Keep that set
  a sub-tree, not the whole graph.
`aix code graph` (alias `aix code complexity`) measures all of this deterministically. It builds **A**, the code's
dependency graph (re-export facades collapsed), and **B**, the ideal shape of the same nodes under this page's
principle: every node a leaf or a composer, arcs only downward, no cycle, no hub. B is constructed from A: cycles
broken at the fewest arcs (Eades, Lin & Smyth 1993), upward arcs cut, levels assigned by longest path from the
leaves, hubs split into a leaf part and a composer part. The **distance A → B** is the list of edits, each with its
reason; a direct arc next to a longer path is not one. Separately it reports stable nodes (Martin's instability ≤
0.25; depending on them is free reuse), propagation cost, Lakos' NCCD and Newman's modularity Q. What B does not
know is printed with it: calls the tool could not resolve, and meaning. Run it before reasoning about the code;
`review-code-review` runs it on every diff and `aix code graph --gate` fails CI on any CUT.

## Evidence (this is established engineering, not taste)
- Parnas, *On the Criteria To Be Used in Decomposing Systems into Modules*, 1972 — one design decision per module.
- Stevens, Myers, Constantine, *Structured Design*, 1974 — coupling and cohesion.
- McIlroy — the Unix philosophy: do one thing well, compose through narrow interfaces.
- Martin — Acyclic Dependencies Principle and Stable Dependencies Principle (depend toward stability).
- Lakos, *Large-Scale C++ Software Design* — levelization; cycles explode build and test cost.
- MacCormack, Rusnak, Baldwin, *Exploring the Structure of Complex Software Designs*, 2006 — propagation cost;
  lower in Linux than in pre-rewrite Mozilla.
- Cai & Kazman, design-rule-space studies — files in dependency cycles carry a disproportionate share of bugs and churn.
- Sturtevant, *System Design and the Cost of Architectural Complexity*, MIT 2013 — files in the cyclic core: several
  times the defect density, lower developer productivity, higher turnover.
- Mo, Cai, Kazman, Xiao, Feng, *Decoupling Level*, ICSE 2016 — architecture anti-patterns predict maintenance cost.
- Simon, *The Architecture of Complexity*, 1962 — near-decomposable hierarchies; Newman & Girvan, 2004 — modularity Q.
- Eades, Lin & Smyth, *A Fast and Effective Heuristic for the Feedback Arc Set Problem*, 1993 — where B breaks a cycle.
- Martin, *OO Design Quality Metrics*, 1994 — instability; depend toward stability. Murphy, Notkin & Sullivan,
  *Software Reflexion Models*, 1995 — checking code against an intended structure (the upward-dependency check).
- Cargo (Rust) and Go refuse to compile dependency cycles between crates/packages.

## Fixing a finding
Each `aix code graph` edit has a skill: CUT → `refactor-cycle`, SPLIT → `refactor-hub`; `aix code dead` → `refactor-dead`; `aix code clones` → `refactor-clone`. One finding per change, verified by re-running the tool and the tests.

## Anti-patterns to name in reviews
`utils`/`common`/`helpers` modules that import project state · "god" services · sibling domains importing each
other · a model importing its repository · circular type imports patched with lazy imports · a shared base class
that knows its subclasses.
