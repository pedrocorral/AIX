"""`aix code isolations` and `aix code affected`: the named parts of the code, who may use whom, what each exposes,
the contracts, the data boundaries and the ADR that governs them. The rules on small declarations (a family: the
parent's files use its parts, a part uses its parent, siblings are free until one declares may_use; a top
isolation uses only what it names; every isolation entered must expose the file); the declaration's own errors
(a widening part, a part outside its parent, a file in two isolations); the proposal (the code's shape minus its
defects: a cycle and an upward edge left out, and nothing else found); contracts (a removed name or a new required
parameter breaks, a new optional one does not); data (a field outside its isolation, a field reaching a logger
through a local); governance (no ADR, a proposed one, an accepted one, a changed declaration); then the command
end to end in a project, and the tests a change reaches."""
import subprocess, sys, tempfile, textwrap, unittest
from pathlib import Path

from helpers import KIT, install, project_cmd, temp_home

sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import isodata, isodecl, isogov, isopropose, isorules, isosurface  # noqa: E402


def decl(isolations: dict, **top) -> isodecl.Decl:
    d = isodecl.Decl({"isolations": isolations, **top})
    isodecl.check_shape(d)
    return d


def kinds(d, edges) -> dict:
    out = {}
    for a, b in edges:
        v = isorules.judge(d, a, b)
        out[(a, b)] = v.kind if v else None
    return out


FAMILY = {
    "app": {"paths": ["src/**"], "exposes": []},
    "app.orders": {"paths": ["src/orders/**"], "exposes": ["src/orders/api.py"], "may_use": ["app.persistence"]},
    "app.billing": {"paths": ["src/billing/**"], "exposes": ["src/billing/api.py"]},
    "app.persistence": {"paths": ["src/persistence/**"], "exposes": ["src/persistence/ports.py", "src/persistence/factory.py"]},
    "app.persistence.postgres": {"paths": ["src/persistence/postgres/**"], "exposes": ["src/persistence/postgres/repo.py"], "may_use": []},
    "lib": {"paths": ["lib/**"]},
}


class Rules(unittest.TestCase):
    def test_the_family_and_the_allow_list(self):
        d = decl(FAMILY)
        got = kinds(d, [
            ("src/main.py", "src/orders/api.py"),                          # the root's own file uses a part: exposed
            ("src/main.py", "src/orders/internal.py"),                     # ... not exposed: hidden
            ("src/persistence/factory.py", "src/persistence/postgres/repo.py"),   # parent's file -> its part
            ("src/persistence/postgres/repo.py", "src/persistence/ports.py"),     # part -> its parent's file
            ("src/persistence/postgres/repo.py", "src/persistence/helpers.py"),   # ... even one it does not expose
            ("src/orders/api.py", "src/persistence/ports.py"),             # named in may_use, exposed
            ("src/orders/api.py", "src/persistence/postgres/repo.py"),     # entering persistence: not exposed by it
            ("src/orders/api.py", "src/billing/api.py"),                   # orders declares may_use without billing
            ("src/billing/api.py", "src/orders/api.py"),                   # billing declares nothing: siblings free
            ("src/billing/api.py", "src/orders/internal.py"),              # ... but the file must be exposed
            ("src/persistence/postgres/repo.py", "src/orders/api.py"),     # postgres declares [] : nothing outside
            ("src/main.py", "lib/x.py"),                                   # a top isolation names nothing
        ])
        self.assertEqual(list(got.values()), [None, "HIDDEN", None, None, None, None, "HIDDEN", "FORBIDDEN", None, "HIDDEN", "FORBIDDEN", "FORBIDDEN"], got)

    def test_naming_a_part_enters_it_directly(self):
        spec = dict(FAMILY, wiring={"paths": ["wiring/**"], "may_use": ["app.persistence.postgres"]})
        d = decl(spec)
        self.assertIsNone(isorules.judge(d, "wiring/main.py", "src/persistence/postgres/repo.py"), "named: entered at the part, which exposes the file")
        self.assertEqual(isorules.judge(d, "wiring/main.py", "src/persistence/ports.py").kind, "FORBIDDEN", "the parent itself is not named")

    def test_declaration_errors(self):
        d = decl({
            "app": {"paths": ["src/**"], "may_use": ["lib"], "colour": "red"},
            "app.orders": {"paths": ["src/orders/**", "other/**"], "may_use": ["ghost", "billing"]},
            "lib": {"paths": ["lib/**"], "exposes": ["src/orders/api.py"]},
            "billing": {"paths": ["src/orders/x.py"]},
            "x.y": {"paths": ["x/**"]},
        }, data={"card": {"fields": ["pan"], "stays_in": ["nowhere"]}})
        isodecl.check_files(d, ["src/orders/api.py", "other/o.py", "src/orders/x.py", "lib/l.py"])
        text = "\n".join(d.errors)
        for expected in ("unknown key `colour`", "`ghost`: no such isolation", "widens the parent: `app` may not use `billing`",
                         "parent `x` is not declared", "stays_in `nowhere`", "other/o.py, which its parent `app` does not",
                         "`lib` exposes src/orders/api.py, which is not one of its files", "held by unrelated isolations"):
            self.assertIn(expected, text)

    def test_what_nothing_uses_is_offered_for_removal(self):
        d = decl(FAMILY)
        edges = {("src/main.py", "src/orders/api.py")}
        files = ["src/main.py", "src/orders/api.py", "src/billing/api.py", "src/persistence/ports.py"]
        self.assertIn(("app.orders", "app.persistence"), isorules.unused_permissions(d, edges))
        self.assertIn(("app.billing", "src/billing/api.py"), isorules.unused_exposes(d, edges, files))
        self.assertNotIn(("app.orders", "src/orders/api.py"), isorules.unused_exposes(d, edges, files))

    def test_globs(self):
        rx = isodecl.glob_regex
        self.assertTrue(rx("src/orders/**").match("src/orders/a/b.py"))
        self.assertTrue(rx("src/orders").match("src/orders/x.py"))
        self.assertFalse(rx("src/orders/").match("src/ordersx/y.py"))
        self.assertFalse(rx("src/*.py").match("src/a/b.py"))
        self.assertTrue(rx("**/api.py").match("src/x/api.py"))


class Proposal(unittest.TestCase):
    FILES = ["src/main.py", "src/orders/api.py", "src/orders/rules.py", "src/billing/api.py", "src/models/order.py",
             "src/services/pay.py", "src/shared/money.py", "tests/test_x.py"]
    EDGES = {("src/main.py", "src/orders/api.py"), ("src/orders/api.py", "src/billing/api.py"), ("src/billing/api.py", "src/orders/rules.py"),
             ("src/orders/api.py", "src/shared/money.py"), ("src/models/order.py", "src/services/pay.py"), ("tests/test_x.py", "src/orders/rules.py")}

    def test_the_code_minus_its_defects(self):
        raw, left_out = isopropose.propose(["src", "tests"], self.FILES, self.EDGES)
        isos = raw["isolations"]
        self.assertEqual(sorted(isos), ["src", "src.billing", "src.models", "src.orders", "src.services", "src.shared"], "tests are exempt, not an isolation")
        reasons = {(a, b): why for a, b, why, _e in left_out}
        self.assertIn("src/orders/api.py", isos["src.orders"]["exposes"], "what outside code uses")
        self.assert_exposed_only_for_kept_edges(isos, {e for _a, _b, _why, e in left_out})
        self.assertIn("points up the layers", reasons[("src.models", "src.services")])
        self.assertEqual(len([k for k, why in reasons.items() if "cycle" in why]), 1, "one cut breaks the orders/billing cycle")
        d = isodecl.Decl(raw); isodecl.check_shape(d)
        isodecl.check_files(d, [f for f in self.FILES if not f.startswith("tests/")])
        self.assertEqual(d.errors, [])
        flagged = {(a, b) for a, b in self.EDGES if not a.startswith("tests/") and isorules.judge(d, a, b)}
        self.assertEqual(len(flagged), 2, f"only the left-out edges fail: {flagged}")

    def assert_exposed_only_for_kept_edges(self, isos: dict, cut: set):
        kept_targets = {b for a, b in self.EDGES if (a, b) not in cut}
        for n, spec in isos.items():
            self.assertFalse(set(spec["exposes"]) - kept_targets, f"{n} exposes a file only a defect reaches")

    def test_yaml_round_trip(self):
        raw, left_out = isopropose.propose(["src"], self.FILES[:-1], self.EDGES)
        from yamlmini import parse_tree
        text = isopropose.to_yaml(raw, left_out)
        self.assertEqual(parse_tree(text)["isolations"], raw["isolations"])
        self.assertIn("# Left out (defects to fix, not permissions):", text)


class Contracts(unittest.TestCase):
    def test_what_breaks_a_caller(self):
        self.assertTrue(isosurface.compatible("(a, b=)", "(a, b=, c=)", "python"))
        self.assertFalse(isosurface.compatible("(a, b=)", "(a, b=, c)", "python"), "a new required parameter breaks")
        self.assertTrue(isosurface.compatible("(a)", "(a, b?)", "js"))
        self.assertFalse(isosurface.compatible("(a)", "(a, b)", "rust"), "Rust has no default")
        self.assertEqual(isosurface.breaking({"f": "(a)", "g": "()"}, {"f": "(a, b)"}, "python"), [("f", "changed (a) -> (a, b)"), ("g", "removed")])

    def test_surfaces(self):
        py = isosurface._python("__all__ = ['f']\ndef f(a, *, b=1): pass\ndef g(): pass\n")
        self.assertEqual(py, {"f": "(a, *, b=)"})
        js = isosurface._js("export function place(cart, opts?) {}\n// export function gone() {}\nexport { a as b }\n")
        self.assertEqual(js, {"place": "(cart, opts?)", "b": "name"})
        java = isosurface._java("public class C { public C(int x) {} public void run(Map<String, Integer> m) {} void hidden() {} }")
        self.assertEqual(java, {"C": "class", "C(int)": "method", "run(Map<String,Integer>)": "method"})
        self.assertEqual(isosurface._rust("pub fn f(a: u8) {}\nfn g() {}\npub struct S;\n"), {"f": "(a)", "S": "struct"})


class Data(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="aix-iso-data-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.root, True))

    def write(self, rel: str, text: str):
        (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.root / rel).write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")

    def test_outside_and_sinks(self):
        self.write("src/payments/charge.py", """
            import logging
            log = logging.getLogger(__name__)
            def charge(card):
                n = card.card_number   # the card number
                log.info("charging %s", n)
                print("done")
            """)
        self.write("src/orders/api.py", "# card_number is mentioned only in this comment\ndef f(order):\n    return order.cvv\n")
        self.write("web/pay.ts", "// console.log(cvv)\nconsole.log('paid', card.cvv);\n")
        d = decl({"payments": {"paths": ["src/payments/**"]}, "orders": {"paths": ["src/orders/**"]}, "web": {"paths": ["web/**"]}},
                 data={"card": {"fields": ["card_number", "cvv"], "stays_in": ["payments"]}})
        files = ["src/payments/charge.py", "src/orders/api.py", "web/pay.ts"]
        outside = isodata.outside(d, files, self.root)
        self.assertEqual([(f, line) for f, line, _m in outside], [("src/orders/api.py", 3), ("web/pay.ts", 2)], "a comment never counts")
        sinks = isodata.sinks(d, files, self.root)
        self.assertIn(("src/payments/charge.py", 5), [(f, line) for f, line, _m in sinks], "through the local `n`")
        self.assertIn(("web/pay.ts", 2), [(f, line) for f, line, _m in sinks])
        self.assertNotIn(6, [line for f, line, _m in sinks if f.endswith("charge.py")], "print('done') carries no field")


class Governance(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="aix-iso-gov-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.root, True))
        (self.root / isogov.DECISIONS).mkdir(parents=True)
        (self.root / isogov.DECISIONS / "INDEX.md").write_text("| Path | What | Status |\n|---|---|---|\n", encoding="utf-8")
        (self.root / isodecl.DECL).write_text("isolations:\n  a: {paths: [a/**]}\n", encoding="utf-8")
        self.raw = isodecl.load(self.root).raw

    def test_no_adr_then_proposed_then_accepted_then_changed(self):
        ok, why = isogov.governance(self.raw, self.root)
        self.assertFalse(ok); self.assertIn("no accepted ADR", why)
        adr = isogov.write_adr(self.raw, [], self.root)
        self.assertEqual(adr.name, "ADR-0001-isolations.md")
        self.assertIn("ADR-0001-isolations.md", (self.root / isogov.DECISIONS / "INDEX.md").read_text(encoding="utf-8"))
        ok, why = isogov.governance(self.raw, self.root)
        self.assertFalse(ok); self.assertIn("is `proposed`", why)
        adr.write_text(adr.read_text(encoding="utf-8").replace("status: proposed", "status: accepted"), encoding="utf-8")
        self.assertTrue(isogov.governance(self.raw, self.root)[0])
        wider = {"isolations": {"a": {"paths": ["a/**"], "may_use": ["b"]}, "b": {"paths": ["b/**"]}}}
        ok, why = isogov.governance(wider, self.root)
        self.assertFalse(ok); self.assertIn("the rules changed after ADR-0001-isolations.md", why)
        self.assertEqual(isogov.write_adr(wider, [], self.root).name, "ADR-0002-isolations.md")

    def test_codeowners_block_is_managed_and_idempotent(self):
        d = decl({"orders": {"paths": ["src/orders/**"], "owner": "@orders"}}, owners={"rules": "@arch"})
        (self.root / ".github").mkdir()
        (self.root / ".github" / "CODEOWNERS").write_text("* @everyone\n", encoding="utf-8")
        for _ in range(2):
            isogov.write_codeowners(isogov.codeowners(d), self.root)
        text = (self.root / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("* @everyone\n"), "a person's lines are kept")
        self.assertEqual(text.count(isogov.OWNERS_BEGIN), 1)
        self.assertIn("/src/orders/ @orders", text)
        self.assertIn("/docs/requirements/isolations.yaml @arch", text)


class Command(unittest.TestCase):
    """The whole loop in a project: propose, the ADR a person accepts, a clean gate, then each kind of finding."""
    FILES = {
        "src/main.py": "from src.orders.api import place\nfrom src.persistence.factory import repository\n",
        "src/orders/api.py": "# @implements FR-ORDERS-001\nfrom src.billing.api import charge\nfrom src.persistence.ports import Repo\ndef place(cart, coupon=None):\n    charge(1)\n",
        "src/billing/api.py": "# @implements FR-ORDERS-001\ndef charge(amount):\n    return amount\n",
        "src/persistence/ports.py": "class Repo:\n    pass\n",
        "src/persistence/factory.py": "from src.persistence.postgres.repo import PgRepo\ndef repository():\n    return PgRepo()\n",
        "src/persistence/postgres/repo.py": "from src.persistence.ports import Repo\nclass PgRepo(Repo):\n    pass\n",
        "src/shared/money.py": "# @implements FR-ORDERS-001\nclass Money:\n    pass\n",
        "tests/test_orders.py": "from src.persistence.postgres.repo import PgRepo\n",
    }

    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        for rel, text in self.FILES.items():
            (self.project / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.project / rel).write_text(text, encoding="utf-8")
        install(self.home, self.project)

    def iso(self, *args, check=False):
        return project_cmd(self.project, self.home, "code", "isolations", *args, check=check)

    def accept_as_a_person(self):
        for adr in (self.project / "docs/requirements/decisions").glob("ADR-*-isolations.md"):
            adr.write_text(adr.read_text(encoding="utf-8").replace("status: proposed", "status: accepted"), encoding="utf-8")

    def test_nothing_declared_passes(self):
        r = self.iso("--gate")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("nothing declared", r.stdout)

    def test_the_loop(self):
        self.iso("--propose", "--depth", "2", "--write", check=True)
        self.assertIn("`isolations.yaml`", (self.project / "docs/requirements/INDEX.md").read_text(encoding="utf-8"))
        r = self.iso("--gate")
        self.assertEqual(r.returncode, 1); self.assertIn("no accepted ADR", r.stdout)
        self.assertIn("status: proposed", self.iso("--accept", check=True).stdout)
        self.assertIn("waiting for a person", self.iso("--accept", check=True).stdout, "a second accept writes no second ADR")
        self.accept_as_a_person()
        r = self.iso("--gate")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.violate()
        r = self.iso("--gate")
        self.assertEqual(r.returncode, 1)
        for kind, what in (("FORBIDDEN", "src/billing/api.py -> src/orders/api.py"), ("HIDDEN", "src/persistence/postgres/repo.py  ("),
                           ("BREAKING", "`place` changed (cart, coupon=) -> (cart, region, coupon=)"), ("GOVERNANCE", "")):
            self.assertIn(kind.lower() + " 1", r.stdout.replace("findings: ", ""), r.stdout)
            self.assertIn(what, r.stdout)

    def violate(self):
        orders = self.project / "src/orders/api.py"
        orders.write_text(orders.read_text(encoding="utf-8").replace("def place(cart, coupon=None)", "def place(cart, region, coupon=None)")
                          + "from src.persistence.postgres.repo import PgRepo\n", encoding="utf-8")
        billing = self.project / "src/billing/api.py"
        billing.write_text(billing.read_text(encoding="utf-8") + "from src.orders.api import place\n", encoding="utf-8")
        decl_file = self.project / isodecl.DECL
        decl_file.write_text(decl_file.read_text(encoding="utf-8") + "# a comment changes nothing\n", encoding="utf-8")
        decl_file.write_text(decl_file.read_text(encoding="utf-8").replace("tests: exempt", "tests: exempt\nowners: {rules: \"@arch\"}"), encoding="utf-8")

    def test_context_codeowners_and_requirements(self):
        self.iso("--propose", "--depth", "2", "--write", check=True)
        out = self.iso("--context", "src/orders/api.py", check=True).stdout
        self.assertIn("Isolation `src.orders`", out)
        self.assertIn("src.persistence: src/persistence/factory.py, src/persistence/ports.py", out, "the files to read, nothing else of them")
        self.assertIn("must not use: src.shared", out)
        self.assertIn("SCATTERED  FR-ORDERS-001", self.iso("--requirements", check=True).stdout)
        self.assertNotEqual(self.iso("--codeowners").returncode, 0, "no owner declared: nothing to write")

    def test_task_start_names_the_isolations_in_scope(self):
        self.iso("--propose", "--depth", "2", "--write", check=True)
        project_cmd(self.project, self.home, "task", "new", "Pricing rule")
        task = next((self.project / "docs/road-map/pending/next").glob("TASK-*-pricing-rule.md"))
        task.write_text(task.read_text(encoding="utf-8").replace("scope: []", "scope: [src/persistence/postgres/]", 1), encoding="utf-8")
        out = project_cmd(self.project, self.home, "task", "start", task.name[:9]).stdout
        self.assertIn("isolations in scope: src.persistence.postgres; before editing: aix code isolations --context src.persistence.postgres", out)


class Affected(unittest.TestCase):
    def test_the_tests_a_change_reaches(self):
        home = temp_home(self); project = home / "app"
        files = {"src/a.py": "X = 1\n", "src/b.py": "from src.a import X\n", "src/c.py": "Y = 2\n", "tests/test_b.py": "from src.b import *\n"}
        for rel, text in files.items():
            (project / rel).parent.mkdir(parents=True, exist_ok=True)
            (project / rel).write_text(text, encoding="utf-8")
        install(home, project)
        git = lambda *a: subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=project, capture_output=True, check=True)
        git("init", "-q"); git("add", "-A"); git("commit", "-qm", "base")
        (project / "src/a.py").write_text("X = 3\n", encoding="utf-8")
        (project / "src/c.py").write_text("Y = 4\n", encoding="utf-8")
        self.assertEqual(project_cmd(project, home, "code", "affected", "--plain").stdout.split(), ["tests/test_b.py"], "a -> b -> test_b; c reaches no test")
        out = project_cmd(project, home, "code", "affected").stdout
        self.assertIn("no test reaches these changed files", out)
        self.assertIn("src/c.py", out)


if __name__ == "__main__":
    unittest.main()
