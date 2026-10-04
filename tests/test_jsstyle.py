"""JS/TS style after the ESLint benchmark (section 14): named function shapes are units (a function expression on a
property or module.exports, an object-literal member, a class field holding an arrow, a getter, a named callback),
a destructured parameter or an inline type in the head does not cut the body, a TypeScript signature without a body
is not a function, and the unused-name check is silent on a commented parameter, a parameter property, a comment
inside an import list and commented-out requires."""
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
