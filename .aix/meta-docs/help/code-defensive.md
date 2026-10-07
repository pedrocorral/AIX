aix code defensive [PATH...] [--all] [--gate] [--report]

DEFENSIVE PROGRAMMING: how guarded the code is. Python only for now (JS/TS, Rust and Java are counted as not
read). Tests are excluded. Four count lines, then the listed spots with what to do, then the recommendation the
counts call for.

  annotations   functions fully typed (every parameter and the return annotated), functions with no typed
                parameter, functions that return None under an annotation that promises a value. No checker,
                pydantic or your own, can work on a function without types.
  guards        pydantic: models, how many are strict (`model_config = ConfigDict(strict=True)`), fields with a
                value rule (`Field(gt=0)`, `max_length=`, `pattern=`), validators, functions under
                `@validate_call` and how many of those are strict. Without strict, pydantic converts: `"5"` for an
                `int` becomes 5 and no error is raised. "pydantic not imported" when nothing checks an argument.
  doors         where outside data enters: `json.load`, `yaml.safe_load`, `tomllib.load`, `pickle.load`,
                Flask/Django `request.form|args|json|POST|GET|data|values|files`, and the parameters of a
                FastAPI handler. A door is checked when its value goes into a model or a constructor
                (`Config(**data)`, `Config.model_validate(...)`), an `isinstance`, an `int(...)`, or, for a
                handler parameter, carries a type (FastAPI checks what is typed).
  inside        an `assert` used as a check in production code (`python -O` removes every assert), an
                `open()` that is not a `with` item, not returned to the caller, and never closed in the function.

Listed spots
  RETURN  f(): returns None (line N) under `-> str`      gated   annotate `-> str | None` or raise
  OPEN    open() without `with` and no close()           gated   `with open(...) as f:`
  DOOR    json.load(...) reaches the code unchecked      advice  parse it into a strict pydantic model, or check its shape
  DOOR    f(): parameter `q` has no type                 advice  annotate it; FastAPI checks what is typed
  ASSERT  assert as a check                              advice  `python -O` removes it; raise ValueError
A function whose annotation names None, `Optional`, `Any` or `object`, or that never returns a value (a stub,
`raise NotImplementedError`), is honest. A function that ends in `sys.exit(...)` does not fall off the end.
Swallowed exceptions (`except: pass`) and mutable default arguments are reported by `aix code style`, not here.

Recommendation lines, in this order, only when the counts call for them
  N functions carry no parameter type: annotate them first
  add pydantic: `@validate_call(config=ConfigDict(strict=True))` on the functions behind the doors, outside data
  parsed into models; a project that allows no dependencies writes one decorator of its own
  N of M models are not strict: set `ConfigDict(strict=True)`
  N doors unchecked: parse each into a model, or check its shape where it is read

  --gate      exit 1 on any RETURN or OPEN finding (advice never fails the gate)
  --all       every listed spot instead of the first 30
  --report    also write docs/tests/code-defensive.md
Examples
  aix code defensive backend
  aix code defensive backend --gate
Why pydantic: measured against beartype and typeguard on the same function (docs/tests/benchmark-engines.md,
section 21): pydantic in strict mode checks everything beartype checks, carries value rules in the annotation,
and most projects already depend on it. Fix with: skill implement-code-python.
