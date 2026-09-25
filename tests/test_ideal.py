"""25. The ideal graph B and the distance A -> B: known answers on small graphs (a tree is already ideal, a
shortcut is not an edit, one cycle costs one cut named with its members, one upward arc one cut, one hub one
split, a composition root is never split), then the report and the gate on a small Python project."""
import sys, unittest
from helpers import KIT, install, project_cmd, temp_home

sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import ideal  # noqa: E402


def graph(*arcs):
    edges = {tuple(a.split(">")) for a in arcs}
    return {n for e in edges for n in e}, edges


class KnownAnswers(unittest.TestCase):
    def test_tree_is_already_ideal(self):
        b = ideal.build(*graph("a>b", "a>c", "b>d", "c>e"))
        self.assertEqual(b["distance"], 0)
        self.assertEqual(b["levels"], {"a": 2, "b": 1, "c": 1, "d": 0, "e": 0})
        self.assertEqual(b["roles"], {"a": "root", "b": "composer", "c": "composer", "d": "leaf", "e": "leaf"})

    def test_shortcut_is_not_an_edit(self):
        b = ideal.build(*graph("a>b", "b>c", "a>c"))
        self.assertEqual(b["distance"], 0, "a downward arc is legitimate however many paths reach it")

    def test_one_cycle_one_cut_with_members(self):
        b = ideal.build(*graph("a>b", "b>c", "c>a", "a>d"))
        self.assertEqual(len(b["cuts"]), 1)
        (arc, why), = b["cuts"].items()
        self.assertIn("closes a cycle among 3 nodes", why)
        self.assertEqual(b["distance"], 1)
        self.assertNotIn(arc, b["b_edges"])

    def test_upward_arc_is_cut(self):
        b = ideal.build(*graph("x/models/m.py>x/services/s.py", "x/services/s.py>x/models/n.py"))
        self.assertEqual(list(b["cuts"].values()), ["upward: layer 1 -> layer 3"])
        self.assertEqual(b["distance"], 1)

    def test_hub_is_split_root_is_not(self):
        b = ideal.build(*graph("p>h", "q>h", "r>h", "h>x", "h>y", "h>z"))
        self.assertEqual(b["roles"]["h"], "hub")
        self.assertEqual(b["splits"], {"h": (3, 3)})
        self.assertIn(("h (composer)", "h (leaf)"), b["b_edges"])
        self.assertIn(("p", "h (leaf)"), b["b_edges"]); self.assertIn(("h (composer)", "x"), b["b_edges"])
        self.assertEqual(b["distance"], 1)
        c = ideal.build(*graph("main.py>u", "main.py>v", "main.py>w", "main.py>x", "main.py>y", "main.py>z"))
        self.assertEqual(c["roles"]["main.py"], "root"); self.assertEqual(c["distance"], 0)
        d = ideal.build(*graph("p>main.py", "q>main.py", "main.py>x"))
        self.assertEqual(d["distance"], 2, "an arc into the composition root is upward: cut")

    def test_edit_lines_and_summary(self):
        b = ideal.build(*graph("a>b", "b>a", "p>h", "q>h", "r>h", "h>x", "h>y", "h>z"))
        lines = ideal.edit_lines(b)
        self.assertTrue(any(l.startswith("  CUT    ") and "closes a cycle" in l for l in lines))
        self.assertTrue(any(l.startswith("  SPLIT  h  (in 3, out 3)") for l in lines))
        self.assertIn("distance A -> B: 2 edits  (cuts: 1 cycle, 0 upward; splits: 1)", ideal.summary_line(b))


class Report(unittest.TestCase):
    def test_report_gate_and_roles(self):
        home = temp_home(self)
        project = home / "app"
        (project / "src").mkdir(parents=True)
        (project / "src" / "leaf.py").write_text("def work(x):\n    return x\n", encoding="utf-8")
        (project / "src" / "mid.py").write_text("from leaf import work\nimport top\n\ndef run(x):\n    return work(x) + top.N\n", encoding="utf-8")
        (project / "src" / "top.py").write_text("import mid\nN = 1\n\ndef main():\n    return mid.run(1)\n", encoding="utf-8")
        install(home, project)
        project_cmd(project, home, "code", "find", "--yes")
        out = project_cmd(project, home, "code", "graph").stdout
        self.assertIn("A (the code):", out)
        self.assertIn("B (ideal:", out)
        self.assertRegex(out, r"distance A -> B: 1 edits  \(cuts: 1 cycle, 0 upward; splits: 0\)")
        self.assertRegex(out, r"CUT    src/(mid|top)\.py -> src/(top|mid)\.py  \(closes a cycle among 2 nodes")
        self.assertNotIn("SHORTCUT", out)
        r = project_cmd(project, home, "code", "graph", "--gate", check=False)
        self.assertEqual(r.returncode, 1); self.assertIn("1 cycle(s)", r.stderr)
        roles = project_cmd(project, home, "code", "graph", "--roles").stdout
        self.assertRegex(roles, r"\s+0  leaf      in\s+1 out\s+0  src/leaf\.py")
        funcs = project_cmd(project, home, "code", "graph", "--functions").stdout
        self.assertRegex(funcs, r"resolved calls \d+ of \d+")
        self.assertIn("(calls resolved by name)", funcs)


if __name__ == "__main__":
    unittest.main()
