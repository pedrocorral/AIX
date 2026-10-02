"""The lessons: the notes skill created (never copied) in .aix/custom/, its generated index and checks, and the layer
refresh that keeps it: custom/ merged by default (--override-custom replaces it), org/ overridden (--merge-org merges)."""
import unittest
from helpers import FIXTURES, KIT, assert_healthy, install, make_fork, project_cmd, temp_home, upgrade

NOTES = (".aix", "custom", "skills", "core", "lessons-learnt-notes")
LESSON = """---
rule: "{rule}"
author: someone@example.com
scope: project
updated: 2026-10-02
---
**Why:** the agent did it without being asked (2026-10-02).
**How to apply:** ask first.
"""


def notes(project):
    return project.joinpath(*NOTES)


def add_lesson(folder, slug, rule):
    (folder / "lessons").mkdir(parents=True, exist_ok=True)
    (folder / "lessons" / f"{slug}.md").write_text(LESSON.format(rule=rule), encoding="utf-8")


class FreshProject(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        self.out = install(self.home, self.project).stdout

    def test_created_empty_linked_and_healthy(self):
        skill = notes(self.project) / "SKILL.md"
        self.assertIn("created (empty lessons)", self.out)
        self.assertIn("No lessons yet.", skill.read_text(encoding="utf-8"))
        self.assertTrue((self.project / ".claude" / "skills" / "core-lessons-learnt-notes" / "SKILL.md").exists())
        self.assertIn("core-lessons-learnt-notes", (self.project / "AGENTS.md").read_text(encoding="utf-8"))
        assert_healthy(self, self.project, self.home)

    def test_kit_checkout_holds_none(self):
        self.assertFalse(notes(KIT).exists(), "the kit's .aix/custom/ would ship its lessons to every project")

    def test_index_and_check(self):
        add_lesson(notes(self.project), "ask-first", "Ask before running anything destructive.")
        r = project_cmd(self.project, self.home, "lessons", "check", check=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("stale", r.stdout)
        d = project_cmd(self.project, self.home, "doctor", check=False)
        self.assertIn("lessons: the index is stale", d.stdout)
        project_cmd(self.project, self.home, "lessons", "index")
        self.assertIn("Ask before running anything destructive.", (notes(self.project) / "SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("0 problem(s)", project_cmd(self.project, self.home, "lessons", "check").stdout)
        assert_healthy(self, self.project, self.home)  # an edited lesson is not drift

    def test_malformed_lesson_and_cap(self):
        (notes(self.project) / "lessons").mkdir()
        (notes(self.project) / "lessons" / "bad.md").write_text("---\nrule: \"x\"\nscope: team\n---\nno sections\n", encoding="utf-8")
        for i in range(21):
            add_lesson(notes(self.project), f"l{i:02d}", f"Rule {i}.")
        project_cmd(self.project, self.home, "lessons", "index")
        out = project_cmd(self.project, self.home, "lessons", "check", check=False).stdout
        for expected in ("no `author:`", "scope `team`", "no **Why:**", "over the cap of 20"):
            self.assertIn(expected, out)


class Refresh(unittest.TestCase):
    """A fork whose custom/ carries one skill; the project wrote a lesson and a file of its own."""
    def setUp(self):
        self.home = temp_home(self)
        self.fork = make_fork(self.home, custom=FIXTURES / "custom-layer")
        self.project = self.home / "app"
        install(self.home, self.project, kit=self.fork)
        add_lesson(notes(self.project), "ours", "Our rule.")
        project_cmd(self.project, self.home, "lessons", "index")
        self.mine = self.project / ".aix" / "custom" / "instructions" / "mine.md"
        self.mine.parent.mkdir(parents=True)
        self.mine.write_text("---\nid: project/mine\ndescription: a project standard\nalways: true\n---\nBe nice.\n", encoding="utf-8")
        self.org_local = self.project / ".aix" / "org" / "local-edit.md"
        self.org_local.write_text("edited by hand in the project\n", encoding="utf-8")

    def test_merge_by_default_keeps_the_project_and_overrides_org(self):
        r = upgrade(self.project, self.home, kit=self.fork)
        self.assertIn("-> .aix/custom/ (merge)", r.stdout)
        self.assertIn("-> .aix/org/ (override)", r.stdout)
        self.assertIn("holds 1 lesson(s): kept (the source has none)", r.stdout)
        self.assertTrue((notes(self.project) / "lessons" / "ours.md").exists())
        self.assertTrue(self.mine.exists(), "a file only the project has survives the merge")
        self.assertFalse(self.org_local.exists(), "org/ is the company repository's: replaced whole")
        assert_healthy(self, self.project, self.home)

    def test_source_lessons_merge_and_the_index_is_rebuilt(self):
        add_lesson(self.fork.joinpath(*NOTES), "theirs", "Their rule.")
        r = upgrade(self.project, self.home, kit=self.fork)
        self.assertIn("merged with the source's 1", r.stdout)
        index = (notes(self.project) / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Our rule.", index)
        self.assertIn("Their rule.", index)

    def test_override_custom_and_merge_org(self):
        r = upgrade(self.project, self.home, "--override-custom", "--merge-org", kit=self.fork)
        self.assertIn("DELETED", r.stdout)
        self.assertFalse(self.mine.exists())
        self.assertIn("No lessons yet.", (notes(self.project) / "SKILL.md").read_text(encoding="utf-8"), "recreated empty, never copied")
        self.assertTrue(self.org_local.exists())


if __name__ == "__main__":
    unittest.main()
