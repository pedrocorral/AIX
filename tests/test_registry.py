"""9. Third-party skills from the registry (network): add a classed skill, it becomes the class implementation; update; remove.
Runs only with AIX_TEST_NETWORK=1 (downloads a tarball from GitHub)."""
import unittest
from helpers import assert_healthy, config, has_network, install, project_cmd, temp_home


@unittest.skipUnless(has_network(), "set AIX_TEST_NETWORK=1 to run the download tests")
class RegistryDownloads(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        install(self.home, self.project)

    def test_classed_entry_becomes_the_implementation(self):
        r = project_cmd(self.project, self.home, "skills", "add", "grill-me")
        self.assertIn("now the implementation of coach-grill-me", r.stdout)
        skill = self.project / ".aix" / "skills" / "extern" / "grill-me" / "SKILL.md"
        text = skill.read_text(encoding="utf-8")
        self.assertIn("name: coach-grill-me", text)
        self.assertIn("class: coach/grill-me", text)
        self.assertIn('id: "@mattpocock/grill-me"', text)
        self.assertRegex(config(self.project), r'(?m)^  coach-grill-me: "@mattpocock/grill-me"')
        info = project_cmd(self.project, self.home, "skills", "info", "coach-grill-me").stdout
        self.assertIn("@mattpocock/grill-me", info)
        self.assertIn("also:        coach-grill-me (kit layer)", info)
        project_cmd(self.project, self.home, "skills", "use", "coach-grill-me", "default")
        self.assertIn("id:          coach-grill-me", project_cmd(self.project, self.home, "skills", "info", "coach-grill-me").stdout)
        project_cmd(self.project, self.home, "skills", "update", "grill-me")
        project_cmd(self.project, self.home, "skills", "remove", "grill-me")
        self.assertFalse(skill.exists())
        self.assertNotRegex(config(self.project), r"(?m)^use:")
        assert_healthy(self, self.project, self.home)

    def test_bare_entry_keeps_its_name(self):
        project_cmd(self.project, self.home, "skills", "add", "caveman", "--on-demand")
        self.assertTrue((self.project / ".claude" / "skills" / "caveman").exists())
        project_cmd(self.project, self.home, "skills", "remove", "caveman")
        assert_healthy(self, self.project, self.home)


if __name__ == "__main__":
    unittest.main()
