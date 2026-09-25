aix code graph [PATH...] [--functions] [--roles] [--gate] [--max-distance N] [--report] [--selftest]     alias: aix code complexity

THE MODULARITY METRIC. Two graphs on the same nodes: A, the code as it is, and B, the ideal shape those nodes
would have under the principle of architecture/modularity.md. The distance A -> B is a list of edits; do them and
A is B. 0 edits = the code already has the ideal shape.

What A is
  modules (default)   nodes = source files; edges = imports between project files. Python, JavaScript/TypeScript,
                      Rust, Java. External packages ignored; unresolved imports ignored, never guessed.
  --functions         nodes = functions/methods; edges = calls resolved by name: a function of the same file, a
                      name imported by name, this.m() / self.m() inside a class or impl, Class.m() / Type::m() on a
                      class defined or imported in the file, module.f() through a module import. Python by the
                      stdlib parser; JavaScript/TypeScript, Rust and Java by tokens. A method on a value whose
                      class the tool does not know is not an arc and not counted. The report says how many of the
                      calls that could target project code it matched; the rest are absent from A and from B.
  PATH...             restrict to these folders (default: the `code_roots` of .aix/config.yaml that exist, else the
                      whole project without hidden, docs, dependency and build folders)
  facades collapsed   an __init__.py / index.ts / mod.rs that only re-exports its own folder is a name, not a
                      module; edges into it go to what it re-exports.

What B is (ideal.py)
  the principle       every node is a leaf (does work, calls nothing that changes) or a composer (wires leaves and
                      lower composers); arcs go only downward; no cycle; no hub.
  built from A        1. every cycle is broken at the fewest arcs a greedy ordering finds (Eades, Lin & Smyth 1993);
                      2. every upward arc is cut: into a composition root, or from a lower layer into a higher one
                         (models/core 1 < adapters/ports 2 < services 3 < controllers 4, by folder name);
                      3. every node gets a level: leaves are 0, a composer is one above the highest node it calls;
                      4. a hub (fan-in and fan-out both >= 3, not a composition root) is split into a leaf part that
                         keeps its callers and a composer part that keeps its calls.
  the distance        the number of edits, each listed with its reason:
                        CUT    A -> B  (closes a cycle among 3 nodes: ...)      defect: break the cycle
                        CUT    A -> B  (upward: layer 1 -> layer 3)              defect: invert through a port
                        SPLIT  X  (in 5, out 6): keep the work as a leaf, move the calls to a composer above it
                      A direct arc next to a longer path (A -> C beside A -> B -> C) is NOT an edit: a downward arc
                      is legitimate however many paths reach it.
  --roles             every node with its level in B, its role in A (leaf, composer, root, hub), fan-in, fan-out.

The shape numbers (A, for trends)
  stable nodes        instability I = out / (in + out) (Martin 1994). I <= 0.25 = stable: value types, models,
                      ports, pure helpers. Depending on a stable node is free reuse; the rest are edges into nodes
                      that change.
  cycles, upward      the cuts above, counted. Defects; the gate fails on them.
  hubs                fan-in >= 3 AND fan-out >= 3; composition roots are hubs by design and never split.
  propagation cost    average share of the graph reachable from a node (MacCormack, Rusnak & Baldwin 2006).
  NCCD                Lakos' normalised cumulative component dependency: 1.0 = a balanced binary tree.
  modularity Q        Newman-Girvan Q of the folder partition at depths 1, 2, 3: ~0 = folders mean nothing
                      structurally, 0.3-0.7 = real clusters with few edges between them.

What B does not know (printed on every report)
  unresolved calls    a call the tool could not match (a method on an object it never saw created, a callback, a
                      dispatch table) is absent from A and therefore from B. The resolved ratio says how much of
                      the truth the graphs hold. Name-based in every language: two functions of one name in one
                      file are one node; Rust trait dispatch and Java interfaces are the main blind spots. A ratio
                      under about 70 % says B is built on a thin A.
  meaning             roles come from shape. A SPLIT says where the shape breaks; whether that is the right cut,
                      and which side of the split is the leaf, is the reader's design decision.

Dead code (--dead)
  DEAD MODULES        files no entry module reaches through imports. Entry modules are live by definition:
                      composition roots and entry points (main, app, index, server, manage, wsgi, cli, ...),
                      tests (tests/, test/, __tests__/, spec/, Maven's src/it), tool/framework config (*.config.*,
                      *rc.js, dot-files), facades, any Python file with an `if __name__ == "__main__"` guard, and what
                      a framework loads by convention: Django migrations/admin/apps/urls/management commands, Cargo
                      lib.rs/build.rs/benches/examples/src/bin, scripts/, public/, and Java classes the container
                      instantiates (@Controller, @RestController, @Service, @Component, @Repository, @Entity, JAX-RS
                      @Path, JUnit). TypeScript imports through tsconfig/jsconfig `baseUrl` and `paths` (`@/x`,
                      `extends`, solution-style `references`) resolve. A folder a string in code names
                      (`'data/static/codefixes'`, `Path('templates/')`) is loaded as data: its files are live.
                      Reachability, not fan-in: an orphan cluster importing itself is dead.
  DEAD FUNCTIONS      with --functions, Python only: a function or method whose simple name is never referenced
                      anywhere else, as a bare name or an attribute. Decorated functions (routes, fixtures,
                      commands are called by the framework), dunder and implicit names, `__all__` exports and
                      entry/test code are excluded. Name-based like vulture, so a method called through any object
                      of the same name is live, `from m import f` is a use: conservative, few false positives, some
                      misses. A public name is tagged: in a library it is API used outside the repository.
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
  --gate                exit 1 on any CUT (cycle, upward dependency); --max-distance N also fails past N edits (CI)
  --report              also write docs/tests/dependency-graph.md
  --selftest            run the built-in cases with known answers (chain, diamond, direct arc, cycle, reuse, layer
                        skip, upward, hub, composition root)

Coverage: static analysis. The graph is only as complete as the imports/calls it can resolve; the tool never guesses.
Used by: review-code-review on every diff (compare before/after), architecture-design-app, the definition of done.
