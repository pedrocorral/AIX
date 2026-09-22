"""6. Skills: listing, info, use/default between implementations of one class, disable/enable, unknown names."""
import unittest
from helpers import KIT, assert_healthy, config, install, project_cmd, temp_home

ACME = KIT / "examples" / "acme"


class SkillsInAnOrganisationProject(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        install(self.home, self.project, "--from", ACME)

    def test_list_and_info(self):
        out = project_cmd(self.project, self.home, "skills").stdout
        self.assertIn("SKILL", out)
        self.assertIn("recommended", out)
        self.assertIn("core-sdd-workflow", out)
        info = project_cmd(self.project, self.home, "skills", "info", "implement-endpoint").stdout
        self.assertIn("layer:       org", info)
        self.assertIn("@acme/django-endpoint", info)
        self.assertIn("aix skills use implement-endpoint implement-endpoint", info, "the alternative must show its use line")

    def test_use_and_default(self):
        project_cmd(self.project, self.home, "skills", "use", "implement-endpoint", "implement-endpoint")
        info = project_cmd(self.project, self.home, "skills", "info", "implement-endpoint").stdout
        self.assertIn("layer:       kit", info)
        self.assertIn("chosen by config use", info)
        self.assertRegex(config(self.project), r'(?m)^  implement-endpoint: "implement-endpoint"', "use: map entry")
        target = (self.project / ".claude" / "skills" / "implement-endpoint" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: implement-endpoint", target)
        project_cmd(self.project, self.home, "skills", "use", "implement-endpoint", "default")
        info = project_cmd(self.project, self.home, "skills", "info", "implement-endpoint").stdout
        self.assertIn("layer:       org", info)
        self.assertNotRegex(config(self.project), r"(?m)^use:")
        assert_healthy(self, self.project, self.home)

    def test_use_rejects_unknown_implementation(self):
        r = project_cmd(self.project, self.home, "skills", "use", "implement-endpoint", "nope", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Known:", r.stdout + r.stderr)


class SkillsSwitches(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        install(self.home, self.project)

    def test_disable_unlinks_and_enable_relinks(self):
        link = self.project / ".claude" / "skills" / "core-find-doc"
        self.assertTrue(link.exists())
        project_cmd(self.project, self.home, "skills", "disable", "core-find-doc")
        self.assertFalse(link.exists())
        self.assertRegex(config(self.project), r"(?m)^disabled_skills: \[core-find-doc\]")
        self.assertIn("disabled", project_cmd(self.project, self.home, "skills", "info", "core-find-doc").stdout)
        project_cmd(self.project, self.home, "skills", "enable", "core-find-doc")
        self.assertTrue(link.exists())
        assert_healthy(self, self.project, self.home)

    def test_show_and_unknown(self):
        self.assertIn("---", project_cmd(self.project, self.home, "skills", "show", "core-find-doc").stdout)
        r = project_cmd(self.project, self.home, "skills", "info", "nope", check=False)
        self.assertNotEqual(r.returncode, 0)

    def test_registry_listing_shows_classes(self):
        out = project_cmd(self.project, self.home, "skills", "registry").stdout
        self.assertIn("caveman", out)
        self.assertIn("class coach/grill-me", out)


if __name__ == "__main__":
    unittest.main()
