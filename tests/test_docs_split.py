"""14. The docs split: projects are seeded from .aix/templates/docs (never from the kit's own docs/), the layers overlay
the seed and the pointer texts, custom wins over org, and upgrade never touches a project's docs."""
import shutil, unittest
from helpers import FIXTURES, KIT, assert_healthy, install, make_fork, project_cmd, temp_home, upgrade

ACME = KIT / "examples" / "acme"


class SeedFromTemplate(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        self.r = install(self.home, self.project)

    def test_project_docs_come_from_the_template_not_from_the_kits_docs(self):
        self.assertIn("seeded: docs (kit)", self.r.stdout)
        docs = self.project / "docs"
        self.assertTrue((docs / "INDEX.md").exists() and (docs / "requirements" / "decisions" / "ADR-0001-adopt-aix-and-choose-stack.md").exists())
        self.assertTrue((docs / "requirements" / "functional" / "example").is_dir(), "the EXAMPLE domain is the seed")
        for kit_only in ("requirements/decisions/ADR-0001-one-positive-payload-list.md", "requirements/decisions/ADR-0005-kit-docs-and-seed-split.md",
                         "tests/suite.md", "road-map/completed/2026-09/TASK-0003-aix-code-security-deterministic-code-side-security.md"):
            self.assertFalse((docs / kit_only).exists(), f"{kit_only} is the kit's own, it must not travel")
        state = (docs / "road-map" / "going-on" / "STATE.md").read_text(encoding="utf-8")
        self.assertNotIn("Kit 2.", state, "no kit history in a project's STATE.md")
        self.assertIn("active_task: none", state)
        assert_healthy(self, self.project, self.home)

    def test_the_kits_own_docs_never_travel(self):
        kit_docs = {p.relative_to(KIT / "docs").as_posix() for p in (KIT / "docs").rglob("*.md")}
        seed = {p.relative_to(KIT / ".aix" / "templates" / "docs").as_posix() for p in (KIT / ".aix" / "templates" / "docs").rglob("*.md")}
        for rel in kit_docs - seed:
            self.assertFalse((self.project / "docs" / rel).exists(), rel)

    def test_seed_is_never_touched_by_upgrade(self):
        marker = self.project / "docs" / "MINE.md"
        marker.write_text("mine\n", encoding="utf-8")
        state = self.project / "docs" / "road-map" / "going-on" / "STATE.md"
        state.write_text(state.read_text(encoding="utf-8").replace("active_task: none", "active_task: TASK-0042"), encoding="utf-8")
        upgrade(self.project, self.home)
        self.assertTrue(marker.exists())
        self.assertIn("active_task: TASK-0042", state.read_text(encoding="utf-8"))

    def test_a_project_without_docs_gets_them_on_install(self):
        shutil.rmtree(self.project / "docs")
        r = project_cmd(self.project, self.home, "install")
        self.assertIn("seeded: docs", r.stdout)
        self.assertTrue((self.project / "docs" / "INDEX.md").exists())


class LayersOverlayTheSeed(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.fork = make_fork(self.home, org=ACME, custom=FIXTURES / "custom-layer")
        org_docs = self.fork / ".aix" / "org" / "templates" / "docs"
        (org_docs / "operations").mkdir(parents=True)
        (org_docs / "operations" / "ORG-RUNBOOK.md").write_text("# Organisation runbook\n", encoding="utf-8")
        (org_docs / "INDEX.md").write_text("# docs/ — organisation index\n", encoding="utf-8")
        org_ptr = self.fork / ".aix" / "org" / "templates" / "pointers"
        org_ptr.mkdir(parents=True)
        (org_ptr / "CLAUDE.md").write_text("Organisation pointer. Read and follow `AGENTS.md` at the repository root.\n", encoding="utf-8")
        cust_docs = self.fork / ".aix" / "custom" / "templates" / "docs"
        cust_docs.mkdir(parents=True)
        (cust_docs / "INDEX.md").write_text("# docs/ — custom index\n", encoding="utf-8")
        self.project = self.home / "app"
        self.r = install(self.home, self.project, kit=self.fork)

    def test_org_files_are_added_and_custom_wins_over_org_over_kit(self):
        self.assertIn("seeded: docs (kit < org < project)", self.r.stdout)
        docs = self.project / "docs"
        self.assertTrue((docs / "operations" / "ORG-RUNBOOK.md").exists(), "an org file is added")
        self.assertTrue((docs / "operations" / "deployment.md").exists(), "the kit's files stay")
        self.assertEqual((docs / "INDEX.md").read_text(encoding="utf-8"), "# docs/ — custom index\n", "custom wins over org over kit")
        assert_healthy(self, self.project, self.home)

    def test_pointer_text_comes_from_the_layer(self):
        claude = (self.project / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertTrue(claude.startswith("Organisation pointer."))
        gemini = (self.project / "GEMINI.md").read_text(encoding="utf-8")
        self.assertIn("`.agents/skills/`", gemini, "a pointer the layer does not override keeps the kit's text")


if __name__ == "__main__":
    unittest.main()
