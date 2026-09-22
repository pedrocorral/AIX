"""4. The layers .aix/org/ and .aix/custom/: one rule for both. Copied at install when the origin has the folder,
replaced at upgrade when it has it, left alone when it does not; --from, --from-org, --from-custom."""
import shutil, unittest
from helpers import FIXTURES, KIT, assert_healthy, config, install, make_fork, project_cmd, temp_home, upgrade

ACME = KIT / "examples" / "acme"


class ForkWithOrgAndCustom(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.fork = make_fork(self.home, org=ACME, custom=FIXTURES / "custom-layer")
        self.project = self.home / "app"
        r = install(self.home, self.project, kit=self.fork)
        self.assertIn("layer org: from the origin", r.stdout)
        self.assertIn("layer custom: from the origin", r.stdout)

    def test_both_layers_arrive_and_resolve(self):
        self.assertTrue((self.project / ".aix" / "org" / "profiles" / "web-app.yaml").exists())
        self.assertTrue((self.project / ".aix" / "custom" / "skills" / "coach" / "teach" / "SKILL.md").exists())
        info = project_cmd(self.project, self.home, "skills", "info", "coach-teach").stdout
        self.assertIn("layer:       project", info, "the project's custom/ must win over org and kit")
        info = project_cmd(self.project, self.home, "skills", "info", "implement-endpoint").stdout
        self.assertIn("@acme/django-endpoint", info)
        project_cmd(self.project, self.home, "profile", "use", "web-app")
        assert_healthy(self, self.project, self.home)

    def test_fork_edit_reaches_the_project_on_upgrade(self):
        marker = self.fork / ".aix" / "org" / "AGENTS.md"
        marker.write_text(marker.read_text(encoding="utf-8") + "\nEdited in the fork.\n", encoding="utf-8")
        new = self.fork / ".aix" / "org" / "skills" / "newthing"
        new.mkdir()
        (new / "SKILL.md").write_text('---\nname: workflow-newthing\nclass: workflow/newthing\nid: "@acme/newthing"\n'
                                      "description: A skill a colleague added to the fork after the first install; used by the test suite.\n---\n# new\n", encoding="utf-8")
        r = upgrade(self.project, self.home, kit=self.fork)
        self.assertIn("layer org: from the origin", r.stdout)
        self.assertIn("Edited in the fork.", (self.project / ".aix" / "org" / "AGENTS.md").read_text(encoding="utf-8"))
        info = project_cmd(self.project, self.home, "skills", "info", "workflow-newthing").stdout
        self.assertIn("layer:       org", info)
        assert_healthy(self, self.project, self.home)

    def test_project_keeps_custom_when_the_origin_drops_it(self):
        shutil.rmtree(self.fork / ".aix" / "custom")
        r = upgrade(self.project, self.home, kit=self.fork)
        self.assertNotIn("layer custom", r.stdout)
        self.assertTrue((self.project / ".aix" / "custom" / "skills" / "coach" / "teach" / "SKILL.md").exists())
        assert_healthy(self, self.project, self.home)


class BareLayerSources(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)

    def test_from_bare_folder_then_from_custom_on_upgrade(self):
        project = self.home / "app"
        r = install(self.home, project, "--from", ACME)
        self.assertIn("org layer from", r.stdout)
        self.assertTrue((project / ".aix" / "org" / "profiles" / "web-app.yaml").exists())
        self.assertRegex(config(project), r"(?m)^source: /.*acme", "the source must be recorded as an absolute path")
        r = upgrade(project, self.home, "--from-custom", FIXTURES / "custom-layer")
        self.assertIn("layer custom: from", r.stdout)
        self.assertRegex(config(project), r"(?m)^source_custom: /.*custom-layer")
        r = upgrade(project, self.home)  # no flags: follows the recorded sources
        self.assertIn("layer org: from", r.stdout)
        self.assertIn("layer custom: from", r.stdout)
        info = project_cmd(project, self.home, "skills", "info", "coach-teach").stdout
        self.assertIn("layer:       project", info)
        assert_healthy(self, project, self.home)

    def test_from_org_at_install(self):
        project = self.home / "app"
        r = install(self.home, project, "--from-org", ACME)
        self.assertIn("layer org: from", r.stdout)
        self.assertRegex(config(project), r"(?m)^source_org: /.*acme")
        self.assertNotRegex(config(project), r"(?m)^source: ")
        self.assertTrue((project / ".aix" / "org" / "instructions").is_dir())
        assert_healthy(self, project, self.home)

    def test_plain_install_has_no_layers(self):
        project = self.home / "app"
        r = install(self.home, project)
        self.assertNotIn("layer org", r.stdout)
        self.assertFalse((project / ".aix" / "org").exists())
        self.assertFalse((project / ".aix" / "custom").exists())


if __name__ == "__main__":
    unittest.main()
