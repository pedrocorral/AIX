"""Leaf: `@checked`, the kit's own run-time guard, standard library only (benchmark section 21: the stdlib row). At
decoration it reads the annotations once; on every call it checks each argument against them: a plain class by
isinstance, `Optional[X]` / `X | None` allows None, a generic such as `list[str]` checks the container only, and
`Annotated[int, between(0, 100)]` checks the type and then every condition attached. A failed check raises, with the
function, the parameter, the expectation and the value: `TypeError: read_rule: path must be Path, got str`,
`ValueError: read_rule: weight failed 'between 0 and 100', got 120`. `@checked(result=True)` checks the result too.
Cost: slots bound once, about 0.2 µs per call. Where it goes: the consumer of every door (a parsed file, an answer
from the network, the command line), not every function."""
import functools, inspect, re, typing


class Cond:
    """A named condition on a value: `Cond("between 0 and 100", lambda v: 0 <= v <= 100)`."""
    def __init__(self, text: str, test):
        self.text, self.test = text, test

    def __call__(self, value) -> bool:
        try:
            return bool(self.test(value))
        except (TypeError, ValueError, AttributeError, KeyError):
            return False


def cond(text: str, test) -> Cond:
    return Cond(text, test)


def positive() -> Cond:
    return Cond("positive", lambda v: v > 0)


def non_empty() -> Cond:
    return Cond("non-empty", lambda v: len(v) > 0)


def between(low, high) -> Cond:
    return Cond(f"between {low} and {high}", lambda v: low <= v <= high)


def one_of(*allowed) -> Cond:
    return Cond(f"one of {', '.join(map(str, allowed))}", lambda v: v in allowed)


def matches(pattern: str) -> Cond:
    rx = re.compile(pattern)
    return Cond(f"matching {pattern}", lambda v: isinstance(v, str) and rx.fullmatch(v) is not None)


def has_keys(*keys) -> Cond:
    """A parsed JSON object with the keys the code relies on."""
    return Cond(f"an object with {', '.join(keys)}", lambda v: isinstance(v, dict) and all(k in v for k in keys))


# ---- the shape of one annotation --------------------------------------------------------------------------------

class _Slot:
    """What one parameter must satisfy: the classes it may be (None among them when optional) and its conditions."""
    def __init__(self, name: str, annotation):
        self.name, self.types, self.conds = name, (), []
        self._read(annotation)

    def _read(self, annotation):
        origin = typing.get_origin(annotation)
        if origin is typing.Annotated:
            base, *extras = typing.get_args(annotation)
            self.conds += [c for c in extras if isinstance(c, Cond)]
            return self._read(base)
        if _is_union(origin):
            for arg in typing.get_args(annotation):
                self._read(arg)
            return None
        self.types += _plain_types(annotation, origin)

    def check(self, fname: str, value):
        if self.types and not isinstance(value, self.types):
            want = " | ".join(t.__name__ for t in self.types)
            raise TypeError(f"{fname}: {self.name} must be {want}, got {type(value).__name__}")
        for c in self.conds:
            if value is not None and not c(value):
                raise ValueError(f"{fname}: {self.name} failed '{c.text}', got {value!r}")


def _is_union(origin) -> bool:
    return origin is typing.Union or (origin is not None and getattr(origin, "__name__", "") == "UnionType")


def _plain_types(annotation, origin) -> tuple:
    """The classes one non-union annotation admits: a generic's container, `object` for Any, the class itself, NoneType."""
    if origin is not None:
        return (origin,)
    if annotation is typing.Any:
        return (object,)
    if isinstance(annotation, type):
        return (annotation,)
    return (type(None),) if annotation is None else ()


def _slots(fn) -> tuple:
    """(positional slots by index, slots by name, result slot or None), read once at decoration."""
    hints = typing.get_type_hints(fn, include_extras=True)
    params = list(inspect.signature(fn).parameters)
    by_name = {p: _Slot(p, hints[p]) for p in params if p in hints}
    by_index = [by_name.get(p) for p in params]
    return by_index, by_name, (_Slot("result", hints["return"]) if "return" in hints else None)


def _guard(fn, result: bool):
    by_index, by_name, result_slot = _slots(fn)
    fname = fn.__qualname__

    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        for i, value in enumerate(args):
            if i < len(by_index) and by_index[i] is not None:
                by_index[i].check(fname, value)
        for name, value in kwargs.items():
            if name in by_name:
                by_name[name].check(fname, value)
        out = fn(*args, **kwargs)
        if result and result_slot is not None:
            result_slot.check(fname, out)
        return out
    wrapped.__checked__ = True
    return wrapped


def checked(fn=None, *, result: bool = False):
    """`@checked` or `@checked(result=True)`: every annotated argument checked on every call."""
    if fn is None:
        return lambda f: _guard(f, result)
    return _guard(fn, result)
