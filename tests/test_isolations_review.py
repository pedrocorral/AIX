"""`aix code isolations`, the cases an independent review of 2.22 and 2.23 found: rewriting one block of the
declaration, the YAML reader, malformed declarations, folders with a dot, roots of the same name, scalar data
values, owner lists, a local of one function, signatures with brackets. Each one failed before it was fixed."""
import sys, unittest

from helpers import KIT

sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import isodata, isodecl, isogov, isopropose, isosurface  # noqa: E402


def decl(isolations: dict, **top) -> isodecl.Decl:
    d = isodecl.Decl({"isolations": isolations, **top})
    isodecl.check_shape(d)
    return d


class Robustness(unittest.TestCase):
    """The cases an independent review of 2.22-2.23 found, each one reproduced before it was fixed."""
    def test_rewriting_a_block_finds_it_only_inside_the_isolations_map(self):
        import isoedit
        from yamlmini import parse_tree
        cases = {
            "data first": ("data:\n  payments: {fields: [pan], stays_in: [payments]}\nisolations:\n  payments: {paths: [src/pay/**], frontiers: {\".\": proposed}}\n", "payments", "."),
            "4 spaces": ("isolations:\n    orders:\n        paths: [src/orders/**]\n        frontiers: {\".\": proposed}\n    pay:\n        paths: [src/pay/**]\n", "orders", "."),
            "comment inside": ("isolations:\n  orders:\n    paths: [src/orders/**]\n# a note\n    frontiers: {\".\": proposed}\n  pay: {paths: [src/pay/**]}\n", "orders", "."),
            "slash key": ("isolations:\n  orders: {paths: [src/orders/**], frontiers: {\".\": accepted, \"api/\": proposed}}\n", "orders", "api"),
        }
        for label, (text, name, folder) in cases.items():
            back = parse_tree(isoedit.with_frontiers(text, parse_tree(text), {(name, folder): "accepted"}))
            self.assertEqual(back["isolations"][name]["frontiers"].get(folder), "accepted", label)
            self.assertNotIn("proposed", str(back["isolations"][name]["frontiers"]), label)
            if label == "data first":
                self.assertEqual(back["data"]["payments"], {"fields": ["pan"], "stays_in": ["payments"]}, "the data entry of the same name is untouched")
            if label != "slash key" and label != "data first":
                self.assertIn("pay", back["isolations"], label)

    def test_yaml_keeps_a_hash_inside_a_value_and_refuses_a_duplicate_key(self):
        from yamlmini import parse_tree
        self.assertEqual(parse_tree("a:\n  owner: team#1\n  b: x # c\n")["a"], {"owner": "team#1", "b": "x"})
        with self.assertRaises(ValueError):
            parse_tree("a:\n  frontiers: x\n  frontiers: y\n")

    def test_malformed_declarations_are_errors_not_crashes(self):
        for raw, expected in (({"isolations": ["a", "b"]}, "no `isolations:` map"),
                              ({"isolations": {"orders": "src/orders/**"}}, "expected a map"),
                              ({"isolations": {"o": {"paths": ["o/**"], "owner": {"x": 1}}}}, "`owner` is a name")):
            d = isodecl.Decl(raw); isodecl.check_shape(d)
            self.assertIn(expected, "\n".join(d.errors))

    def test_a_folder_with_a_dot_carries_frontiers(self):
        self.assertEqual(isodecl.base_folder(["src/app.core/**"]), "src/app.core")
        self.assertIsNone(isodecl.base_folder(["src/main.py"]), "a plain file path is no folder")

    def test_two_roots_of_the_same_name_stay_apart(self):
        self.assertEqual(isopropose.top_names(["backend/src", "frontend/src", "lib"]), {"backend/src": "backend-src", "frontend/src": "frontend-src", "lib": "lib"})

    def test_scalar_data_values_and_owner_lists(self):
        d = decl({"pay": {"paths": ["p/**"], "owner": ["@a", "@b"]}}, data={"card": {"fields": "cvv", "stays_in": "pay", "never_to": "logs"}})
        self.assertEqual(isodata.rules(d), [("card", ["cvv"], ["pay"], ["logs"])])
        self.assertEqual(isogov.codeowners(d), ["/p/ @a @b"])

    def test_a_local_of_one_function_never_taints_another(self):
        src = "import logging\nlog = logging.getLogger()\ndef a(card):\n    n = card.card_number\n    return n\ndef b():\n    n = 'safe'\n    log.info(n)\n"
        self.assertEqual(isodata._python_sinks(src, {"card_number"}, ["logs"]), [])

    def test_signatures_with_brackets_inside_their_parameters(self):
        js = lambda s: isosurface._js(s)
        self.assertTrue(isosurface.breaking(js("export function run(a: number, cb: () => void) {}"), js("export function run(a: number, cb: () => void, mode: string) {}"), "js"))
        rs = isosurface._rust
        self.assertTrue(isosurface.breaking(rs("pub fn h(x: Box<dyn Fn(u8) -> u8>) {}"), rs("pub fn h(x: Box<dyn Fn(u8) -> u8>, y: u8) {}"), "rust"))
        self.assertEqual(js("export function f(cb: () => void, n = 2) {}"), {"f": "(cb, n?)"}, "`=>` is no default value")


if __name__ == "__main__":
    unittest.main()
