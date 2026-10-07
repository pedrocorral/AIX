"""Section 21 of docs/tests/benchmark-engines.md: the run-time guard libraries on the same function. Per-call cost of
beartype, typeguard and pydantic's validate_call (default and strict) against a plain call and a stdlib decorator
that checks plain classes with isinstance; what each one says for a wrong list item; whether `"5"` passes for an
`int`. Needs the benchmark venv with the three installed (engines.py); run from a file, typeguard refuses stdin."""
import functools, inspect, sys, timeit
from importlib.metadata import version
from pathlib import Path

N = 300_000


def stdlib_guard(fn):
    """Plain classes checked with isinstance; the slots are bound once, at decoration time."""
    hints = {k: v for k, v in fn.__annotations__.items() if k != "return" and isinstance(v, type)}
    slots = [(i, n, hints[n]) for i, n in enumerate(inspect.signature(fn).parameters) if n in hints]

    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        for i, n, t in slots:
            if i < len(args) and not isinstance(args[i], t):
                raise TypeError(f"{fn.__name__}: {n} must be {t.__name__}, got {type(args[i]).__name__}")
        return fn(*args, **kwargs)
    return wrapped


def plain(f: Path, names: list[str], depth: int) -> str:
    return names[0][:depth]


def cases() -> dict:
    from beartype import beartype
    from pydantic import ConfigDict, validate_call
    from typeguard import typechecked
    strict = ConfigDict(strict=True, arbitrary_types_allowed=True)
    return {"plain call": plain, "stdlib decorator": stdlib_guard(plain), "beartype": beartype(plain), "typeguard": typechecked(plain),
            "pydantic validate_call": validate_call(config=ConfigDict(arbitrary_types_allowed=True))(plain),
            "pydantic validate_call, strict": validate_call(config=strict)(plain)}


def _says(fn, *args) -> str:
    try:
        fn(*args)
        return "no error"
    except Exception as e:   # the message is the point
        return f"{type(e).__name__}: {str(e).splitlines()[0][:90]}"


def main():
    print("versions:", {p: version(p) for p in ("beartype", "typeguard", "pydantic")})
    p, names = Path("x"), ["abc"] * 50
    print(f"{'decorator':32s} {'µs/call':>8s}  names=[1, 2]")
    for label, fn in cases().items():
        t = timeit.timeit(lambda: fn(p, names, 2), number=N) / N * 1e6
        print(f"{label:32s} {t:8.2f}  {_says(fn, p, [1, 2], 2)}")
    from pydantic import ConfigDict, validate_call

    @validate_call
    def loose(n: int) -> int:
        return n

    @validate_call(config=ConfigDict(strict=True))
    def strict(n: int) -> int:
        return n
    print("pydantic default, '5' for an int:", repr(loose("5")), "| strict:", _says(strict, "5"))


if __name__ == "__main__":
    sys.exit(main())
