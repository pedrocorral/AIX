"""19. Pass-through wrappers: a function whose only statement forwards its own parameters to one function is a gated
finding of `aix code style`, in Python, JavaScript/TypeScript, Rust and Java. Named expressions, factories over a
constructor, adapters that add, drop or reorder an argument, framework-decorated and trait/interface methods are not."""
import re, unittest
from helpers import install, project_cmd, temp_home

PY = '''
def forwards(x, y):
    return target(x, y)


def forwards_with_doc(x):
    """Documented, still a wrapper."""
    return target(x)


def forwards_bare_call(x):
    target(x)


def forwards_keywords(x, y):
    return target(y=y, x=x)


def forwards_stars(*args, **kwargs):
    return target(*args, **kwargs)


def forwards_to_module(x):
    return mod.target(x)


def renames():
    return target()


class Thing:
    def forwards_to_method(self, x):
        return self.other(x)

    def __init__(self, x):
        super().__init__(x)


def names_an_expression(x):
    return (ROOT / x).exists()


def factory(x):
    return Thing(x)


def adds_an_argument(x):
    return target(x, 1)


def drops_an_argument(x, y):
    return target(x)


def reorders(x, y):
    return target(y, x)


def transforms(x):
    return target(x.strip())


def computes(x):
    return target(x) + 1


def calls_a_parameter(f, x):
    return f(x)


def two_statements(x):
    y = target(x)
    return y


@app.route("/x")
def route(x):
    return service(x)


def lazy_import():
    import extern
    return extern
'''
PY_WRAPPERS = {"forwards", "forwards_with_doc", "forwards_bare_call", "forwards_keywords", "forwards_stars", "forwards_to_module", "renames", "Thing.forwards_to_method"}

JS = '''
function forwards(x, y) { return target(x, y); }
export function forwardsExported(x) {
  return target(x);
}
const forwardsArrow = (x) => {
  return target(x);
};
async function forwardsAwait(x) { return await target(x); }
function forwardsBare(x) {
  target(x);
}
class Thing {
  forwardsMethod(x) { return this.other(x); }
  constructor(x) { super(x); }
}
function factory(x) { return new Thing(x); }
function addsAnArgument(x) { return target(x, 1); }
function dropsAnArgument(x, y) { return target(x); }
function reorders(x, y) { return target(y, x); }
function transforms(x) { return target(x.trim()); }
function computes(x) { return target(x) + 1; }
function twoStatements(x) { const y = target(x); return y; }
function branches(x) { if (x) { return target(x); } return null; }
'''
JS_WRAPPERS = {"forwards", "forwardsExported", "forwardsArrow", "forwardsAwait", "forwardsBare", "forwardsMethod"}

TS = '''
function forwardsTyped(x: number, y: string): string { return target(x, y); }
export const forwardsArrowTyped = (x: number): string => {
  return target(x);
};
function transformsTyped(x: number): string { return target(String(x)); }
function factoryTyped(x: number): Thing { return new Thing(x); }
'''
TS_WRAPPERS = {"forwardsTyped", "forwardsArrowTyped"}

RS = '''
fn forwards(x: i32, y: &str) -> i32 {
    target(x, y)
}
pub fn forwards_return(x: u8) -> u8 {
    return target(x);
}
pub(crate) fn forwards_path(x: u8) -> u8 {
    other::target(x)
}
fn forwards_generic(x: Vec<(u8, u8)>) -> usize {
    target(x)
}
impl Thing {
    fn forwards_method(&self, x: u8) -> u8 {
        self.other(x)
    }
    fn constructor(x: u8) -> Thing {
        Thing::new(x)
    }
}
impl From<u8> for Thing {
    fn from(x: u8) -> Thing {
        make(x)
    }
}
fn adds_an_argument(x: u8) -> u8 {
    target(x, 1)
}
fn drops_an_argument(x: u8, y: u8) -> u8 {
    target(x)
}
fn method_on_parameter(x: &str) -> bool {
    x.is_empty()
}
fn computes(x: u8) -> u8 {
    target(x) + 1
}
fn two_statements(x: u8) -> u8 {
    let y = target(x);
    y
}
'''
RS_WRAPPERS = {"forwards", "forwards_return", "forwards_path", "forwards_generic", "forwards_method"}

JAVA = '''
package com.acme;
public class Thing {
    public String forwards(String x, int y) { return target(x, y); }
    static int forwardsStatic(int x) {
        return Util.target(x);
    }
    void forwardsVoid(String x) { target(x); }
    public String forwardsGeneric(List<String> x, Map<String, Integer> y) { return target(x, y); }
    public Thing(int x) { super(x); }
    public Thing(int x, int y) { this(x); }
    @Override public String overridden(String x) { return target(x); }
    public static Thing factory(int x) { return new Thing(x); }
    public String addsAnArgument(String x) { return target(x, 1); }
    public String dropsAnArgument(String x, int y) { return target(x); }
    public boolean methodOnParameter(String x) { return x.isEmpty(); }
    public int getX() { return x; }
    public String computes(String x) { return target(x) + "!"; }
    public String twoStatements(String x) { String y = target(x); return y; }
}
'''
JAVA_WRAPPERS = {"forwards", "forwardsStatic", "forwardsVoid", "forwardsGeneric"}

SAMPLES = {"sample.py": (PY, PY_WRAPPERS), "sample.js": (JS, JS_WRAPPERS), "sample.ts": (TS, TS_WRAPPERS), "sample.rs": (RS, RS_WRAPPERS), "Sample.java": (JAVA, JAVA_WRAPPERS)}


class PassThrough(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        (self.project / "src").mkdir(parents=True)
        for name, (src, _) in SAMPLES.items():
            (self.project / "src" / name).write_text(src, encoding="utf-8")
        install(self.home, self.project)

    def flagged(self, name: str) -> set:
        out = project_cmd(self.project, self.home, "code", "style", f"src/{name}", "--all").stdout
        return {m.group(1) for m in re.finditer(rf"src/{re.escape(name)}:(\S+)\s.*pass-through", out)}

    def test_python(self):
        self.assertEqual(self.flagged("sample.py"), PY_WRAPPERS)

    def test_javascript(self):
        self.assertEqual(self.flagged("sample.js"), JS_WRAPPERS)

    def test_typescript(self):
        self.assertEqual(self.flagged("sample.ts"), TS_WRAPPERS)

    def test_rust(self):
        self.assertEqual(self.flagged("sample.rs"), RS_WRAPPERS)

    def test_java(self):
        self.assertEqual(self.flagged("Sample.java"), JAVA_WRAPPERS)

    def test_gate_and_card(self):
        r = project_cmd(self.project, self.home, "code", "style", "src", "--gate", check=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("pass-through", r.stdout)
        self.assertRegex(r.stdout, r"over a limit \d+ \(.*pass-through 25")
        card = project_cmd(self.project, self.home, "code", "style", "src/sample.py:forwards").stdout
        self.assertIn("pass-through: forwards its arguments to `target`", card)
        self.assertIn("inline the call", card)
        clean = project_cmd(self.project, self.home, "code", "style", "src/sample.py:factory").stdout
        self.assertIn("pass-through             no", clean)
        self.assertIn("no findings", clean)


if __name__ == "__main__":
    unittest.main()
