"""17. The help pages: `aix help <topic>` reads .aix/meta-docs/help/<topic>.md, aliases and sub-commands resolve,
an unknown topic lists the pages, a layer replaces a page, and the usage screen carries the skill count."""
import unittest
from helpers import KIT, install, project_cmd, run, temp_home

HELP = KIT / ".aix" / "meta-docs" / "help"


class HelpPages(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)

    def test_topic_is_the_markdown_page(self):
        page = (HELP / "code-graph.md").read_text(encoding="utf-8")
        self.assertEqual(run(["help", "code", "graph"], cwd=KIT, home=self.home).stdout, page + ("" if page.endswith("\n") else "\n"))
        self.assertEqual(run(["code", "graph", "--help"], cwd=KIT, home=self.home).stdout, run(["help", "code", "graph"], cwd=KIT, home=self.home).stdout)

    def test_aliases_and_subcommands(self):
        graph = run(["help", "code", "graph"], cwd=KIT, home=self.home).stdout
        for alias in (["graph"], ["complexity"], ["code", "dead"], ["code", "clones"]):
            self.assertEqual(run(["help", *alias], cwd=KIT, home=self.home).stdout, graph, alias)
        self.assertEqual(run(["help", "rules"], cwd=KIT, home=self.home).stdout, run(["help", "instructions"], cwd=KIT, home=self.home).stdout)
        self.assertEqual(run(["help", "self-test"], cwd=KIT, home=self.home).stdout, run(["help", "self-install"], cwd=KIT, home=self.home).stdout)

    def test_every_page_has_a_topic(self):
        for page in HELP.glob("*.md"):
            if page.name in ("INDEX.md", "usage.md", "about.md"):
                continue
            topic = page.stem.replace("code-", "code ").replace("docs-", "docs ").split(" ")
            self.assertIn("aix", run(["help", *topic], cwd=KIT, home=self.home).stdout, page.name)

    def test_unknown_topic_lists_the_pages(self):
        r = run(["help", "nonsense"], cwd=KIT, home=self.home, check=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no help for 'nonsense'", r.stdout)
        self.assertIn("code graph", r.stdout)
        self.assertIn("self-install", r.stdout)

    def test_usage_and_about_come_from_the_pages(self):
        usage = run([], cwd=KIT, home=self.home).stdout
        self.assertNotIn("{n}", usage, "the skill count is filled in")
        self.assertIn("aix install", usage)
        about = run(["about"], cwd=KIT, home=self.home).stdout
        self.assertEqual(about.strip(), (HELP / "about.md").read_text(encoding="utf-8").strip())

    def test_newie_is_one_screen_and_has_aliases(self):
        out = run(["newie"], cwd=KIT, home=self.home).stdout
        self.assertEqual(out, (HELP / "newie.md").read_text(encoding="utf-8"))
        self.assertLessEqual(out.count("\n"), 40, "one screen, the basics only")
        for alias in ("for-dummies", "basics"):
            self.assertEqual(run([alias], cwd=KIT, home=self.home).stdout, out, alias)
        for level in ("2", "3"):
            page = run(["newie", level], cwd=KIT, home=self.home).stdout
            self.assertEqual(page, (HELP / f"newie-{level}.md").read_text(encoding="utf-8"))
            self.assertLessEqual(page.count("\n"), 40, f"level {level} is one screen")
        r = run(["newie", "9"], cwd=KIT, home=self.home, check=False)
        self.assertEqual(r.returncode, 1); self.assertIn("the chain ends at 3", r.stderr)

    def test_a_layer_replaces_a_page(self):
        project = self.home / "app"
        install(self.home, project)
        self.assertIn("aix install", project_cmd(project, self.home, "help", "install").stdout, "the pages travel with the project")
        custom = project / ".aix" / "custom" / "meta-docs" / "help"
        custom.mkdir(parents=True)
        (custom / "install.md").write_text("aix install — in this company, ask the platform team first.\n", encoding="utf-8")
        self.assertEqual(project_cmd(project, self.home, "help", "install").stdout, "aix install — in this company, ask the platform team first.\n")
        self.assertEqual(project_cmd(project, self.home, "install", "--help").stdout, "aix install — in this company, ask the platform team first.\n")


if __name__ == "__main__":
    unittest.main()
