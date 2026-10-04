"""Leaf: what a Java project declares, for the taint walk to follow a call through the receiver's type instead of
guessing by name. Classes with what they extend and implement, the methods of each file, the declared type of each
field, and the implementations of each interface or parent, one level."""
import re

CLASS_DECL = re.compile(r"\b(?:class|interface|enum|record)\s+(\w+)(?:<[^>{]*>)?(?:\s+extends\s+([\w.<>, ]+?))?(?:\s+implements\s+([\w.<>, ]+?))?\s*(?:\(|\{)")
FIELD_DECL = re.compile(r"^[ \t]*(?:@\w+(?:\([^)]*\))?[ \t]*)*(?:(?:private|protected|public|final|static|transient|volatile)\s+)*(?P<type>[A-Z][\w.]*)(?:<[^>\n]*>)?(?:\[\])*\s+(?P<name>\w+)\s*(?:=|;)", re.M)
LOCAL_DECL = re.compile(r"(?<![\w.])(?:final\s+)?(?P<type>[A-Z][\w.]*)(?:<[^>]*>)?\s+(?P<name>\w+)\s*=")           # `AccountService s = ...`
VAR_NEW = re.compile(r"\bvar\s+(?P<name>\w+)\s*=\s*new\s+(?P<type>[A-Z]\w*)")                                      # `var s = new AccountService()`
RECEIVER_CALL = re.compile(r"(?<![\w$.])(?:new\s+(?P<ctor>[A-Z]\w*)\s*\([^()]*\)|(?P<recv>[\w$]+))\s*\.\s*(?P<method>[\w$]+)\s*\(")   # `s.find(`, `new X().find(`, `X.find(`


class TypeIndex:
    """classes: name -> [file]; parents: name -> [implementing or extending class names]; fields: file -> {name: type};
    methods: file -> {name: (params, statements)}."""
    def __init__(self):
        self.classes, self.parents, self.fields, self.methods, self.lines = {}, {}, {}, {}, {}

    def add_file(self, file, text: str, lines: list, methods: dict):
        self.methods[file], self.lines[file] = methods, lines
        self.fields[file] = {m.group("name"): m.group("type").split(".")[-1] for m in FIELD_DECL.finditer(text)}
        for m in CLASS_DECL.finditer(text):
            self.classes.setdefault(m.group(1), []).append(file)
            for parent in re.split(r"[,\s]+", (m.group(2) or "") + " " + (m.group(3) or "")):
                if parent:
                    self.parents.setdefault(re.sub(r"<.*", "", parent).split(".")[-1], []).append(m.group(1))

    def targets(self, type_name: str, method: str, arity: int) -> list:
        """(file, params, statements) of `method` with `arity` parameters in the class `type_name` and in every class
        that implements or extends it, one level."""
        out = []
        for cls in [type_name] + self.parents.get(type_name, []):
            for file in self.classes.get(cls, []):
                params, statements = self.methods.get(file, {}).get(method, (None, None))
                if params is not None and len(params) == arity:
                    out.append((file, params, statements))
        return out

    def receiver_type(self, m, file, locals_: dict):
        """The declared type of a call's receiver: a constructor, a local declared before, a field of the file, or a
        class name used statically; None when it cannot be read."""
        if m.group("ctor"):
            return m.group("ctor")
        name = m.group("recv")
        if name in locals_:
            return locals_[name]
        if name in self.fields.get(file, {}):
            return self.fields[file][name]
        return name if name in self.classes else None


def local_types(text: str) -> dict:
    """name -> type for the local declarations of one statement."""
    out = {m.group("name"): m.group("type").split(".")[-1] for m in LOCAL_DECL.finditer(text)}
    out.update({m.group("name"): m.group("type") for m in VAR_NEW.finditer(text)})
    return out
