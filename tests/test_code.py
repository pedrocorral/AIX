"""7. The code tools: `aix code find` (list, yes, the checklist through a pseudo-terminal), every tool on a project whose
code is outside the conventional folders, hidden and dependency folders ignored."""
import os, unittest
from helpers import config, fixture, install, project_cmd, temp_home

TOOLS = (["code", "graph"], ["code", "complexity"], ["code", "dead"], ["code", "clones"], ["code", "style"], ["code", "stats"],
         ["code", "security"], ["code", "vulnerabilities"])


class FlatProject(unittest.TestCase):
    """Code in mytool/, nothing under backend/, src/ ..."""
    def setUp(self):
        self.home = temp_home(self)
        self.project = fixture("flat-project", self.home / "flat")
        install(self.home, self.project)

    def test_find_list_reports_and_changes_nothing(self):
        before = config(self.project)
        out = project_cmd(self.project, self.home, "code", "find", "--list").stdout
        self.assertRegex(out, r"mytool\s+2 python\s+\s*new")
        self.assertIn("configured, not found", out)
        self.assertEqual(config(self.project), before)

    def test_find_yes_writes_code_roots_and_tools_use_them(self):
        r = project_cmd(self.project, self.home, "code", "style")
        self.assertIn("scanning the whole project", r.stderr, "with no configured root existing the tools fall back and say so")
        self.assertIn("functions analysed 2", r.stdout)
        out = project_cmd(self.project, self.home, "code", "find", "--yes").stdout
        self.assertIn("code_roots: ['mytool']", out)
        self.assertRegex(config(self.project), r"(?m)^  code_roots: \[mytool\]")
        r = project_cmd(self.project, self.home, "code", "style")
        self.assertNotIn("scanning the whole project", r.stderr)
        self.assertIn("Code style — mytool", r.stdout)

    def test_every_tool_runs_and_ignores_hidden_folders(self):
        for tool in TOOLS:
            r = project_cmd(self.project, self.home, *tool, check=False)
            self.assertEqual(r.returncode, 0, f"{' '.join(tool)}\n{r.stdout}{r.stderr}")
        graph = project_cmd(self.project, self.home, "code", "graph").stdout
        self.assertIn("nodes 2", graph, "main.py and helpers.py; .hidden/x.py must not count")


class MultiProjectFolder(unittest.TestCase):
    """Three projects side by side, AIX installed in the parent folder."""
    def setUp(self):
        self.home = temp_home(self)
        self.project = fixture("multi-project", self.home / "multi")
        install(self.home, self.project)

    def test_find_yes_selects_the_three_projects(self):
        out = project_cmd(self.project, self.home, "code", "find", "--yes").stdout
        self.assertIn("code_roots: ['alpha', 'beta', 'gamma']", out)
        graph = project_cmd(self.project, self.home, "code", "graph").stdout
        self.assertIn("alpha, beta, gamma", graph)
        self.assertIn("nodes 4", graph, "three m.py plus gamma/ui.ts; node_modules ignored")

    def test_find_list_shows_markers(self):
        out = project_cmd(self.project, self.home, "code", "find", "--list").stdout
        self.assertRegex(out, r"alpha\s+1 python\s+python project\s+new")
        self.assertNotIn("node_modules", out)

    @unittest.skipIf(os.name == "nt", "curses checklist: Linux/macOS only")
    def test_checklist_through_a_pseudo_terminal(self):
        """Move to the second row (beta), untick it, apply: code_roots = [alpha, gamma]."""
        from helpers import Terminal
        term = Terminal(self.project, self.home, ["code", "find"], {"LINES": "24", "COLUMNS": "100"})
        term.read(1.5)
        for key in (b"j", b" ", b"\r"):
            term.send(key)
        term.read(1.0)
        term.wait()
        plain = term.plain()
        self.assertIn("space toggle", plain, "the checklist legend must have been drawn")
        for name in ("alpha", "beta", "gamma"):
            self.assertIn(name, plain)
        self.assertRegex(config(self.project), r"(?m)^  code_roots: \[alpha, gamma\]")


if __name__ == "__main__":
    unittest.main()
