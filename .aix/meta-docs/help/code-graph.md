aix code graph [PATH...] [--functions] [--gate] [--max-reducible PCT] [--report] [--selftest]     alias: aix code complexity

THE MODULARITY METRIC. Distance between the real dependency graph and its ideal: the lowest complexity that still
delivers every dependency the code has. The ideal is a baseline, achievable or not; the same baseline for every
project makes the numbers comparable. 0 % = at the baseline.

What it builds
  modules (default)   nodes = source files; edges = imports between project files. Python, JavaScript/TypeScript,
                      Rust, Java. External packages ignored; unresolved imports ignored, never guessed.
  --functions         nodes = functions/methods (Python only, stdlib parser); edges = calls resolved by name in the
                      module, through imported names, and self.method(). Calls through typed objects cannot be
                      resolved statically: the function graph is a lower bound.
  PATH...             restrict to these folders (default: the `code_roots` of .aix/config.yaml that exist, else the
                      whole project without hidden, docs, dependency and build folders)

Normalisations (all reported)
  facades collapsed   an __init__.py / index.ts / mod.rs that only re-exports its own folder is a name, not a
                      module; edges into it go to what it re-exports.
  stable nodes        instability I = out / (in + out) (Martin 1994). I <= 0.25 = stable: value types, models,
                      ports, pure helpers. Depending on a stable node is free reuse (modularity.md); edges into
                      stable nodes are not complexity. Replaces the naive "leaf = no dependencies" rule.
  wiring              edges out of composition roots (composition.py, main.py, app.py, index.ts ...) and tests
                      are never shortcuts: wiring and exercising many modules directly is their job.

The measurement
  complexity          edges into non-stable nodes.
  ideal complexity    transitive reduction (Aho, Garey & Ullman 1972) of the graph with each cycle contracted to
                      one node: the smallest graph with exactly the same reachability. Unique. Every dependency
                      is kept; only shortcuts go (A -> C while A -> B -> C), and each cycle of k nodes is counted
                      at its acyclic minimum, k-1 edges.
  reducible           (complexity - ideal) / ideal in %. THE number. Every counted edge is listed:
                        SHORTCUT  A -> C  also reached via B      drop A -> C, or route C through B
                        cycle edges beyond the minimum            break the cycle
  upward              not part of reducible, listed and gated on their own: an edge into a composition root, or
                      from a lower layer into a higher one (models/core 1 < adapters/ports 2 < services 3 <
                      controllers 4, by folder name). Wrong direction is a defect regardless of reachability.
  cycles              strongly connected components; each listed. Defects.
  hubs                fan-in >= 3 AND fan-out >= 3; composition roots labelled as hubs by design.
  propagation cost    average share of the graph reachable from a node (MacCormack, Rusnak & Baldwin 2006).
  NCCD                Lakos' normalised cumulative component dependency: CCD / CCD of a balanced binary tree of
                      the same size. 1.0 = as coupled as an ideal tree, above = more coupled.
  modularity Q        Newman-Girvan Q of the folder partition at depths 1, 2, 3: ~0 = folders mean nothing
                      structurally, 0.3-0.7 = real clusters with few edges between them.

How to read the result
  cycles or upward > 0       fix first; these are facts, not candidates
  SHORTCUT lines             each is one removable edge; the bypass names the intermediate to route through
  reducible                  distance from the baseline; compare across time and across projects
  NCCD, Q                    shape: tree-likeness and folder cohesion; trend indicators
  a hub that is not a root   split it: keep the stable part, move the rest up to its callers

Dead code (--dead)
  DEAD MODULES        files no entry module reaches through imports. Entry modules are live by definition:
                      composition roots and entry points (main, app, index, server, manage, wsgi, cli, ...),
                      tests, tool/framework config, facades, and any Python file with an `if __name__ ==
                      "__main__"` guard. Reachability, not fan-in: an orphan cluster importing itself is dead.
  DEAD FUNCTIONS      with --functions, Python only: a function or method whose simple name is never referenced
                      anywhere else, as a bare name or an attribute. Decorated functions (routes, fixtures,
                      commands are called by the framework), dunder and implicit names, `__all__` exports and
                      entry/test code are excluded. Name-based like vulture, so a method called through any object
                      of the same name is live: conservative, few false positives, some misses.
  Every line is a candidate: confirm nothing reaches it by string, reflection or a framework before deleting.
  aix code dead --gate fails on any candidate.

Clones (--clones)
  EXACT               groups of functions with the same normalised structure: identifiers -> role, literals ->
                      type, docstrings and comments dropped (clone types 1-2, Roy & Cordy 2007). Found exactly by
                      hashing; Python via the parser, JS/TS/Rust/Java via normalised tokens of the function body.
  NEAR                pairs sharing >= --similarity % (default 70) of winnowed fingerprints (Schleimer, Wilkerson
                      & Aiken 2003, the MOSS algorithm; k-grams of 5 tokens): clone type 3, the copied-and-tweaked
                      function. Functions under 6 lines are ignored. Sorted by size x similarity: biggest wins first.
  Why: clones are the leaf that was never extracted, and clones later changed inconsistently are bugs (Juergens
  et al., ICSE 2009). Every line is a candidate: adapters of one port share a shape legitimately; merge only when
  they share a purpose. aix code clones --gate fails on exact groups only.

Options
  aix code dead         the dead-code report (see above); aix code clones the clone report (--similarity PCT)
  --gate                exit 1 on any cycle, any upward dependency, or reducible > --max-reducible PCT (CI)
  --report              also write docs/tests/dependency-graph.md (generated, git-ignored)
  --selftest            run the built-in cases with known answers (chain, diamond, shortcut, cycle, reuse, layer skip, upward)

Coverage: static analysis. The graph is only as complete as the imports/calls it can resolve; the tool never guesses.
Used by: review-code-review on every diff (compare before/after), architecture-design-app, the definition of done.
