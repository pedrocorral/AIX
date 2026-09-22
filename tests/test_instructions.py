"""5. Instructions and profiles: enable/disable, rendered files per runtime, AGENTS.md blocks, profile sets, the rules alias."""
import unittest
from helpers import assert_healthy, config, install, project_cmd, temp_home


class Instructions(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        install(self.home, self.project)

    def test_list_and_info(self):
        out = project_cmd(self.project, self.home, "instructions").stdout
        self.assertIn("aix/agents/rules", out)
        self.assertIn("optional (off)", out)
        self.assertRegex(out, r"\d+ of \d+ instructions active")
        info = project_cmd(self.project, self.home, "instructions", "info", "aix/frameworks/fastapi-backend").stdout
        self.assertIn("scoped to", info)
        self.assertIn("optional:    True", info)
        self.assertEqual(project_cmd(self.project, self.home, "rules").stdout, out, "aix rules is an alias of aix instructions")

    def test_enable_renders_per_runtime_and_disable_removes(self):
        project_cmd(self.project, self.home, "instructions", "enable", "aix/languages/rust")
        gh = self.project / ".github" / "instructions" / "aix-languages-rust.instructions.md"
        cur = self.project / ".cursor" / "rules" / "aix-languages-rust.mdc"
        self.assertTrue(gh.exists() and cur.exists())
        self.assertIn('applyTo: "**/*.rs', gh.read_text(encoding="utf-8"))
        self.assertIn("globs: **/*.rs", cur.read_text(encoding="utf-8"))
        self.assertIn("aix/languages/rust", (self.project / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertRegex(config(self.project), r"(?m)^instructions: \[aix/languages/rust\]")
        doctor = project_cmd(self.project, self.home, "doctor").stdout
        self.assertIn("1 scoped (aix/languages/rust)", doctor)
        project_cmd(self.project, self.home, "instructions", "disable", "aix/languages/rust")
        self.assertFalse(gh.exists() or cur.exists())
        assert_healthy(self, self.project, self.home)

    def test_disabling_a_block_removes_its_agents_section(self):
        project_cmd(self.project, self.home, "instructions", "disable", "aix/agents/output")
        self.assertNotIn("\n## Output", (self.project / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertRegex(config(self.project), r"(?m)^disabled_instructions: \[aix/agents/output\]")
        project_cmd(self.project, self.home, "instructions", "enable", "aix/agents/output")
        self.assertIn("\n## Output", (self.project / "AGENTS.md").read_text(encoding="utf-8"))
        assert_healthy(self, self.project, self.home)

    def test_unknown_id_fails(self):
        r = project_cmd(self.project, self.home, "instructions", "enable", "aix/nope", check=False)
        self.assertNotEqual(r.returncode, 0)


class Profiles(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        install(self.home, self.project)

    def test_kit_profiles_switch_sets(self):
        listing = project_cmd(self.project, self.home, "profile").stdout
        self.assertIn("fastapi-react", listing)
        self.assertIn("kedro", listing)
        project_cmd(self.project, self.home, "profile", "use", "fastapi-react")
        doctor = project_cmd(self.project, self.home, "doctor").stdout
        for iid in ("aix/frameworks/fastapi-backend", "aix/frameworks/react-frontend", "aix/languages/python", "aix/languages/typescript"):
            self.assertIn(iid, doctor)
        self.assertTrue((self.project / ".github" / "instructions" / "aix-frameworks-fastapi-backend.instructions.md").exists())
        project_cmd(self.project, self.home, "profile", "use", "kedro")
        doctor = project_cmd(self.project, self.home, "doctor").stdout
        self.assertIn("aix/frameworks/kedro-pipelines", doctor)
        self.assertNotIn("aix/frameworks/react-frontend", doctor)
        project_cmd(self.project, self.home, "profile", "off")
        self.assertNotIn("scoped", project_cmd(self.project, self.home, "doctor").stdout)
        assert_healthy(self, self.project, self.home)

    def test_explicit_switch_wins_over_the_profile(self):
        project_cmd(self.project, self.home, "profile", "use", "kedro")
        project_cmd(self.project, self.home, "instructions", "disable", "aix/languages/python")
        doctor = project_cmd(self.project, self.home, "doctor").stdout
        self.assertIn("aix/frameworks/kedro-pipelines", doctor)
        self.assertNotIn("aix/languages/python", doctor)

    def test_unknown_profile_fails(self):
        r = project_cmd(self.project, self.home, "profile", "use", "nope", check=False)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
