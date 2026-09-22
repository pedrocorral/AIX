"""8. A 1.x layout (root framework.yaml, scripts/, skills/, templates/, docs/meta-docs/) migrates to .aix/ on upgrade.
The fixture is generated from a fresh install and turned inside out, so it always matches the current kit's content."""
import shutil, unittest
from helpers import KIT, assert_healthy, install, run, temp_home, upgrade, version_of


def make_legacy(project):
    aix = project / ".aix"
    for src, dst in (("scripts", "scripts"), ("skills", "skills"), ("templates", "templates"), ("meta-docs", "docs/meta-docs"), ("config.yaml", "framework.yaml")):
        (project / dst).parent.mkdir(parents=True, exist_ok=True)
        (aix / src).rename(project / dst)
    for extra in ("bin", "instructions", "profiles", "index.json", "manifest.json"):
        p = aix / extra
        shutil.rmtree(p) if p.is_dir() else p.unlink() if p.exists() else None
    shutil.rmtree(aix)
    for runtime in (".claude", ".github", ".cursor", ".agents", ".opencode"):
        shutil.rmtree(project / runtime, ignore_errors=True)
    fy = project / "framework.yaml"
    fy.write_text(fy.read_text(encoding="utf-8").replace(f"version: {version_of(KIT)}", "version: 1.9.0"), encoding="utf-8")
    (project / "aix").write_text("#!/bin/sh\n# 1.x root launcher\n", encoding="utf-8")


class LegacyLayout(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "old"
        install(self.home, self.project)
        make_legacy(self.project)
        self.assertTrue((self.project / "framework.yaml").exists() and not (self.project / ".aix").exists())

    def test_dry_run_announces_the_migration(self):
        r = run(["upgrade", "--dry-run"], cwd=self.project, home=self.home)
        self.assertIn("1.x layout detected", r.stdout)
        self.assertTrue((self.project / "framework.yaml").exists(), "dry run must move nothing")

    def test_upgrade_migrates_and_ends_healthy(self):
        r = upgrade(self.project, self.home)
        self.assertIn("1.x layout detected", r.stdout)
        self.assertFalse((self.project / "framework.yaml").exists())
        self.assertFalse((self.project / "aix").exists(), "root launcher removed")
        for rel in (".aix/config.yaml", ".aix/scripts/aix.py", ".aix/skills/INDEX.md", ".aix/meta-docs/INDEX.md", ".aix/bin", ".aix/instructions", ".aix/profiles"):
            self.assertTrue((self.project / rel).exists(), rel)
        for rel in ("scripts", "skills", "templates", "docs/meta-docs"):
            self.assertFalse((self.project / rel).exists(), f"{rel} must have moved under .aix/")
        self.assertEqual(version_of(self.project), version_of(KIT))
        assert_healthy(self, self.project, self.home)


if __name__ == "__main__":
    unittest.main()
