aix code style [TARGET...] [--all] [--gate] [--report] [--selftest]

READABILITY, per function, with specific feedback. TARGET is a folder, a file (extension optional), or one
function: path:func, path/func, path::Class.method. A folder or file gives a table ranked worst first; a single
function gives a card: each metric against its limit, then every finding with its line and what to do.

Metrics and limits (.aix/config.yaml `style:` block; sources in .aix/meta-docs/conventions/readability.md)
  lines                  60   NASA/JPL one page; McConnell: a ceiling, not a target
  cognitive complexity   15   Campbell / SonarSource 2017: nesting and breaks in linear flow; built for readability
  cyclomatic complexity  10   McCabe 1976: independent paths = tests needed
  nesting depth           4   Kernighan & Plauger, McConnell
  parameters              5   pylint default; McConnell's hard limit 7
  file lines            400
  leftovers             none  an import nothing in the file uses (JS/TS, Java, Python; a Rust `use` may carry a trait, the
                              compiler warns), a variable assigned and never read, a trailing parameter never read (one
                              before a used parameter is positional: a callback's contract). Not: `_` names, re-export
                              files and names other modules import from this one, decorated, overriding, public or
                              dunder methods, stubs, tests (fixtures arrive by name), req/res/next/err/event callbacks
  swallowed             none  a catch/except that does nothing and says nothing; a bare `except:` whatever it does
                              (a statement or a comment inside the block is intent)
  bugs                  none  a mutable default argument (Python), an assignment inside a condition (JS; wrap it in its
                              own parentheses when you mean it), `==` on a String (Java)
  pass-through          none  a function whose only statement forwards its own parameters to one call: an envelope inside
                              an envelope (agents do it to satisfy the limits). Not one: a decorated function, a factory
                              naming a constructor, a trait/interface method, an adapter that adds, drops or reorders
Advice (not gated): naming (language casing, single-letter names outside loops), missing docstring on a public
function, magic numbers. Evidence for names: Lawrie 2006, Butler 2010, Hofmeister 2017.

Feedback is concrete: "72 lines: the deepest block is lines 40-58, extract it", "cognitive 31: biggest costs at
line 12 (loop, nesting +2) ...", "nesting 5 at lines 44-52: invert the condition and return early",
"6 parameters: group them into one object".

Python is measured exactly (stdlib parser, Sonar's cognitive rules). JS/TS, Rust and Java are measured from
tokens and braces: close for lines, parameters and nesting, approximate for complexity.

Modernise (advice tier, never gated): the report detects the runtime the project targets (pyproject
requires-python, .python-version, the venv, tsconfig target, engines.node, Cargo.toml, pom/Gradle; the header
names the source) and suggests only what that version enables: if/elif ladder -> match (3.10+), Optional[X] ->
X | None (3.10+), typing.List -> list (3.9+), assign-only __init__ -> @dataclass (3.7+), os.path -> pathlib,
toml -> tomllib (3.11+), a && a.b -> a?.b and x !== undefined ? x : d -> x ?? d (ES2020+), var -> const/let,
unwrap-only match -> let-else (Rust 1.65+), switch with breaks -> switch expression (Java 14+).
"Python on PATH (assumed)" means nothing in the project declares a version: declare it in pyproject.
  --gate      exit 1 if any function is over a limit or any file too long (advice never fails the gate)
  --all       full table instead of the top 30
  --report    also write docs/tests/code-style.md
  --selftest  known-answer cases (Sonar's example scores 9, a five-deep nest scores 5, ...)
Examples
  aix code style backend                       ranked table
  aix code style backend/app/notes/services/note_service:create   one function, full card
  aix code style frontend/src/app/App.tsx::handleSaveNote
The stack linters enforce the same limits in the editor: stacks/<lang>/tooling.
