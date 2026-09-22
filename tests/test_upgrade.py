"""3. Upgrade from the previous tagged release: new files added, the project's choices survive, a local edit is flagged."""
import re, unittest
from helpers import KIT, LAUNCHER_NAME, assert_healthy, config, install, previous_kit, project_cmd, run, same_tree, temp_home, upgrade, version_of


class UpgradeFromPreviousRelease(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.prev = previous_kit(self, self.home)
        self.project = self.home / "app"
        install(self.home, self.project, kit=self.prev)
        self.assertEqual(version_of(self.project), version_of(self.prev))
        # the project's own choices, made with its own (old) copy of the CLI
        project_cmd(self.project, self.home, "profile", "use", "fastapi-react")
        project_cmd(self.project, self.home, "instructions", "enable", "aix/languages/rust")
        (self.project / "mytool").mkdir()
        (self.project / "mytool" / "m.py").write_text("x = 1\n", encoding="utf-8")
        text = config(self.project)
        text = re.sub(r"(?m)^  code_roots:.*$", "  code_roots: [mytool]", text, flags=re.M)
        (self.project / ".aix" / "config.yaml").write_text(text, encoding="utf-8")
        agents = self.project / "AGENTS.md"
        agents.write_text(agents.read_text(encoding="utf-8").rstrip("\n") + "\n\n## Project notes\nKeep this line.\n", encoding="utf-8")
        edited = self.project / ".aix" / "scripts" / "doctor.py"
        edited.write_text(edited.read_text(encoding="utf-8") + "\n# local edit\n", encoding="utf-8")

    def test_dry_run_changes_nothing(self):
        before = config(self.project)
        r = run(["upgrade", "--dry-run"], cwd=self.project, home=self.home)
        self.assertIn("dry run", r.stdout)
        self.assertEqual(config(self.project), before)
        self.assertEqual(version_of(self.project), version_of(self.prev))

    def test_upgrade_applies_and_keeps_the_projects_choices(self):
        r = upgrade(self.project, self.home)
        self.assertIn("done", r.stdout)
        self.assertEqual(version_of(self.project), version_of(KIT))
        self.assertEqual(same_tree(KIT / ".aix" / "scripts", self.project / ".aix" / "scripts"), [])
        text = config(self.project)
        self.assertRegex(text, r"(?m)^profile: fastapi-react", "profile lost")
        self.assertRegex(text, r"(?m)^instructions: \[aix/languages/rust\]", "enabled instruction lost")
        self.assertRegex(text, r"(?m)^  code_roots: \[mytool\]", "code_roots lost")
        self.assertIn("Keep this line.", (self.project / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertNotIn("# local edit", (self.project / ".aix" / "scripts" / "doctor.py").read_text(encoding="utf-8"))
        assert_healthy(self, self.project, self.home)
        doctor = project_cmd(self.project, self.home, "doctor").stdout
        self.assertIn("aix/languages/rust", doctor)
        self.assertIn("profile: fastapi-react", doctor)

    def test_local_edit_is_flagged_after_first_upgrade(self):
        upgrade(self.project, self.home)
        edited = self.project / ".aix" / "scripts" / "doctor.py"
        edited.write_text(edited.read_text(encoding="utf-8") + "\n# edit two\n", encoding="utf-8")
        d = project_cmd(self.project, self.home, "doctor", check=False)
        self.assertIn("edited locally", d.stdout)
        plan = run(["upgrade", "--dry-run"], cwd=self.project, home=self.home).stdout
        self.assertIn("LOCAL EDIT", plan)


class UpgradeRefusals(unittest.TestCase):
    def test_a_project_cannot_upgrade_itself(self):
        home = temp_home(self)
        project = home / "app"
        install(home, project)
        r = run(["upgrade", "--yes"], cwd=project, home=home, launcher=project / ".aix" / "bin" / LAUNCHER_NAME, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("cannot upgrade itself", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
