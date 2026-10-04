"""JS/TS style after the ESLint benchmark (section 14): named function shapes are units (a function expression on a
property or module.exports, an object-literal member, a class field holding an arrow, a getter, a named callback),
a destructured parameter or an inline type in the head does not cut the body, a TypeScript signature without a body
is not a function, and the unused-name check is silent on a commented parameter, a parameter property, a comment
inside an import list and commented-out requires. Since 2.21.35 every function with a block body is a unit, a
callback included, named by what it is passed to and its line, each measured on its own code (benchmark section 14
and the two decisions recorded there)."""
import unittest

from helpers import install, project_cmd, temp_home

APP_JS = """'use strict';
/* Fix for A6
const crypto = require("crypto");
const config = require("../../config/config");
*/
const fs = require("fs");

app.init = function init() {
  fs.readFileSync("x");
  return this;
};

module.exports = function query(options) {
  options.parsed = true;
  return function query(req, res, next) {
    if (ret = params[i](name, fn)) {
      next();
    }
  };
};

router.use(path, function mounted_app(req, res, next) {
  next();
});

const resource = {
  index: function (req, res) {
    res.send(1);
  },
  show: (req, res) => {
    res.send(2);
  },
};

const replaceImagePath = (overlay) => {
  const decl = 'loadTexture(' + overlay + ');';
  return decl;
};

function onMouseUp( /* event */ ) {
  return 1;
}
"""

APP_TS = """import {
  faArrowLeft,
  // jhipster-needle-add-icon-import
} from '@fortawesome/free-solid-svg-icons';

export interface IFilterOption {
  hasAnyFilterSet(): boolean;
  addFilter(name: string, ...values: string[]): boolean;
}

export class Registration {
  constructor(
    public login: string,
    public email: string,
  ) {}

  private onUnload = async (reason: string) => {
    return reason + faArrowLeft;
  };

  get text() {
    return this.login;
  }

  remove(series: string): Observable<{}> {
    return of(series);
  }
}

export default function App({ appTitle, useCustom }: AppProps) {
  if (useCustom) {
    return appTitle;
  }
  return "";
}

export const getClientColor = (
  /**
   * any uniquely identifying key
   */
  id: string,
) => {
  return id.length;
};
"""


class JsStyle(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        (self.project / "src").mkdir(parents=True)
        (self.project / "src/app.js").write_text(APP_JS, encoding="utf-8")
        (self.project / "src/app.ts").write_text(APP_TS, encoding="utf-8")
        install(self.home, self.project)
        self.out = project_cmd(self.project, self.home, "code", "style", "src", "--all", check=False).stdout

    def card(self, target: str) -> str:
        return project_cmd(self.project, self.home, "code", "style", target, check=False).stdout

    def test_named_shapes_are_units(self):
        self.assertIn("functions analysed 14", self.out, self.out)
        for name in ("init", "query", "mounted_app", "index", "show", "replaceImagePath", "onMouseUp"):
            self.assertIn(f"src/app.js:{name}  (line", self.card(f"src/app.js:{name}"), name)

    def test_typescript_shapes_and_signatures(self):
        for name in ("constructor", "onUnload", "text", "remove", "App", "getClientColor"):
            self.assertIn(f"src/app.ts:{name}  (line", self.card(f"src/app.ts:{name}"), name)
        for name in ("hasAnyFilterSet", "addFilter"):
            self.assertNotIn("(line", self.card(f"src/app.ts:{name}"), name + " is a signature, not a function")

    def test_destructured_parameter_keeps_the_body(self):
        card = self.card("src/app.ts:App")
        self.assertRegex(card, r"lines\s+6\s", card)
        self.assertRegex(card, r"cyclomatic complexity\s+2\s", card)

    def test_assignment_in_a_condition_inside_a_returned_function(self):
        self.assertIn("app.js:16  bug: assignment inside a condition", self.out, self.out)

    def test_no_false_unused_names(self):
        leftovers = [line for line in self.out.splitlines() if line.startswith("  LINE") and "leftover" in line]
        self.assertEqual(leftovers, [], "\n".join(leftovers))


if __name__ == "__main__":
    unittest.main()


CALLBACKS = """app.get('/users', function (req, res) {
  if (req.query.x) {
    res.send([1, 2].map((n) => {
      if (n > 1) { return n; }
      return 0;
    }));
  }
});
describe('login', () => {
  it('works', async () => {
    const page = await open();
    if (page) { expect(page).toBe(true); }
  });
});
function outer(a) {
  const helper = (b) => {
    if (b) { return a; }
    return b;
  };
  const unused = 1;
  promise.catch(() => {});
  return helper(a);
}
"""


class Callbacks(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        (self.project / "src").mkdir(parents=True)
        (self.project / "src/cb.js").write_text(CALLBACKS, encoding="utf-8")
        install(self.home, self.project)

    def card(self, target: str) -> str:
        return project_cmd(self.project, self.home, "code", "style", target, check=False).stdout

    def test_every_block_bodied_function_is_a_unit_named_by_its_place(self):
        out = project_cmd(self.project, self.home, "code", "style", "src", "--all", check=False).stdout
        self.assertIn("functions analysed 6", out, out)
        for name, line in (("app.get('/users') callback", 1), ("map callback", 3), ("describe('login') callback", 9), ("it('works') callback", 10)):
            self.assertIn(f"src/cb.js:{name} (l.{line})  (line {line}", self.card(f"src/cb.js:{line}"), name)

    def test_each_function_is_measured_on_its_own_code(self):
        self.assertRegex(self.card("src/cb.js:1"), r"cyclomatic complexity\s+2\s", "the handler's own if, not the map callback's")
        self.assertRegex(self.card("src/cb.js:3"), r"cyclomatic complexity\s+2\s")
        self.assertRegex(self.card("src/cb.js:9"), r"lines\s+3\s", "describe owns three lines, the test inside is its own unit")
        outer = self.card("src/cb.js:outer")
        self.assertRegex(outer, r"cyclomatic complexity\s+2\s", "its own `.catch(` only, helper's branch is helper's\n" + outer)
        self.assertRegex(outer, r"lines\s+6\s", outer)

    def test_hygiene_reads_through_nested_functions_and_reports_once(self):
        out = project_cmd(self.project, self.home, "code", "style", "src", "--all", check=False).stdout
        lines = [l for l in out.splitlines() if l.startswith("  LINE")]
        self.assertEqual(len(lines), 2, "\n".join(lines))
        self.assertNotIn("is not camelCase", out, "a callback has no name to judge\n" + out)
        self.assertIn("src/cb.js:20  leftover: variable `unused` in `outer`", out, out)
        self.assertIn("src/cb.js:21  swallowed", out, "an empty `.catch(() => {})` stays with its parent\n" + out)


TRICKY = """describe('Component (list)', () => {
  it('renders {{ x }}', () => {
    const tpl = '<div>{{ name }}</div>';
    expect(tpl).toContain('(');
  });
});
var html = str.replace(/\\{([^}]+)\\}/g, function (_, name) {
  return name;
});
export function useOutsideClick<T extends HTMLElement>(ref: T) {
  return ref;
}
function Picker<T>({ value }: { value: T }) {
  return value;
}
class A {
  static createElement = <
    T extends string,
  >(x: T) => {
    return x;
  };
}
function outer() {
  const s = 'var name = "tj";';
  return s;
}
class S {
  addUserToCollectionIfMissing<Type extends Pick<IUser, 'id'>>(collection: Type[]): Type[] {
    return collection;
  }
  delete(id: string): void {
    this.x.delete(id);
  }
  private handler(state: State): (event: PointerEvent) => void {
    return withBatchedUpdates((e: PointerEvent) => {
      return state.use(e);
    });
  }
}
export const getFormValue = function <T extends Primitive>(x: T) {
  return x;
};
"""


class TrickyText(unittest.TestCase):
    """Parentheses and braces inside single-quoted strings and regex literals do not break a body; generics after a
    function name or before an arrow's parameters are read, nested ones too; `delete` is a method name; a returned
    function type is a return type; a string holding a double quote is not code."""
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        (self.project / "src").mkdir(parents=True)
        (self.project / "src/t.tsx").write_text(TRICKY, encoding="utf-8")
        install(self.home, self.project)
        self.out = project_cmd(self.project, self.home, "code", "style", "src", "--all", check=False).stdout

    def test_units_and_bodies(self):
        self.assertIn("functions analysed 12", self.out, self.out)
        for name in ("useOutsideClick", "Picker", "createElement", "outer", "addUserToCollectionIfMissing", "delete", "handler", "getFormValue"):
            card = project_cmd(self.project, self.home, "code", "style", f"src/t.tsx:{name}", check=False).stdout
            self.assertRegex(card, r"lines\s+[34]\s", name + "\n" + card)

    def test_no_false_findings(self):
        self.assertEqual([l for l in self.out.splitlines() if l.startswith("  LINE")], [], self.out)
