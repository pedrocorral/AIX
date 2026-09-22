"""2. A fresh install: exactly the payload arrives, nothing else; manifest matches; links; idempotent; --copy; collisions."""
import json, sys, unittest
from helpers import KIT, assert_healthy, install, project_cmd, run, temp_home

sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import payload  # noqa: E402  the one list of what travels


class FreshInstall(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        install(self.home, self.project)

    def test_payload_arrives_exactly(self):
        for rel, mode in payload.items(KIT):
            if mode == payload.LAYER:
                self.assertFalse((self.project / rel).exists(), f"{rel}: the kit has no {rel}, the project must not either")
            else:
                self.assertTrue((self.project / rel).exists(), f"{rel} ({mode}) missing")
        for rel in ("tests", "examples", "AIX-DEVELOPMENT.md", "CHANGELOG.md", ".aix/org", ".aix/custom"):
            self.assertFalse((self.project / rel).exists(), f"{rel} must never travel")

    def test_manifest_hashes_owned_files_only(self):
        recorded = set(json.loads((self.project / ".aix" / "manifest.json").read_text(encoding="utf-8"))["files"])
        owned = {p.as_posix() for p in payload.files(self.project, payload.OWNED)}
        self.assertEqual(recorded, owned)
        self.assertFalse(any(k.startswith((".aix/org", ".aix/custom", ".aix/index", ".aix/manifest")) for k in recorded))

    def test_runtime_links_and_pointers(self):
        for rel in (".claude/skills/core-sdd-workflow", ".github/skills/core-sdd-workflow", ".cursor/skills/core-sdd-workflow",
                    ".agents/skills/core-sdd-workflow", ".opencode/skills/core-sdd-workflow",
                    ".github/copilot-instructions.md", ".cursor/rules/aix.mdc", "GEMINI.md", "CLAUDE.md", ".aix/index.json"):
            self.assertTrue((self.project / rel).exists(), rel)
        agents = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        for section in ("## Rules", "## Navigation", "## Session", "## Output"):
            self.assertIn(section, agents)

    def test_healthy_and_idempotent(self):
        assert_healthy(self, self.project, self.home)
        project_cmd(self.project, self.home, "install")
        assert_healthy(self, self.project, self.home)

    def test_code_find_suggestions_printed_without_terminal(self):
        r = install(self.home, self.home / "app2")
        self.assertIn("Code folders in", r.stdout)
        self.assertIn("no terminal to ask", r.stdout)


class InstallOptions(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)

    def test_copy_mode_makes_real_folders(self):
        project = self.home / "copyapp"
        install(self.home, project, "--copy")
        link = project / ".claude" / "skills" / "core-sdd-workflow"
        self.assertTrue(link.is_dir() and not link.is_symlink())
        assert_healthy(self, project, self.home)

    def test_second_install_with_skip_all(self):
        project = self.home / "twice"
        install(self.home, project)
        marker = project / "docs" / "MINE.md"
        marker.write_text("mine\n", encoding="utf-8")
        r = install(self.home, project, "--skip-all")
        self.assertIn("skipped", r.stdout)
        self.assertTrue(marker.exists())
        assert_healthy(self, project, self.home)

    def test_into_rejects_missing_value(self):
        r = run(["install", "--into"], cwd=KIT, home=self.home, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("needs a directory", r.stdout + r.stderr)
        r = run(["install", "--into", "--copy"], cwd=KIT, home=self.home, check=False)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
