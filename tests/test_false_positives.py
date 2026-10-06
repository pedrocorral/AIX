"""Two false positives reported by an agent on a real project (2.21.43): a pnpm, Yarn or uv workspace keeps one
lockfile at its root, so an app inside it is not "without a lockfile"; a secret in a file that git ignores and does
not track never entered the repository, so it is listed as untracked and not gated."""
import shutil, subprocess, unittest

from helpers import install, project_cmd, temp_home

APP = '{"name": "@acme/web", "private": true, "dependencies": {"react": "^19.0.0"}}\n'


class Workspaces(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        self.project.mkdir(); install(self.home, self.project)

    def test_pnpm_root_lockfile_covers_the_apps(self):
        (self.project / "frontend/apps/web").mkdir(parents=True)
        (self.project / "frontend/pnpm-workspace.yaml").write_text('packages:\n  - "apps/*"\n')
        (self.project / "frontend/pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n")
        (self.project / "frontend/apps/web/package.json").write_text(APP)
        (self.project / "standalone").mkdir(); (self.project / "standalone/package.json").write_text(APP)
        out = project_cmd(self.project, self.home, "code", "security", check=False).stdout
        self.assertNotIn("frontend/apps/web/package.json:1  no lockfile", out, out)
        self.assertIn("standalone/package.json:1  no lockfile next to package.json", out, out)

    def test_yarn_and_uv_workspaces(self):
        (self.project / "js/packages/a").mkdir(parents=True)
        (self.project / "js/package.json").write_text('{"private": true, "workspaces": ["packages/*"]}\n')
        (self.project / "js/yarn.lock").write_text("# yarn lockfile v1\n")
        (self.project / "js/packages/a/package.json").write_text(APP)
        (self.project / "py/libs/b").mkdir(parents=True)
        (self.project / "py/pyproject.toml").write_text('[project]\nname = "mono"\n[tool.uv.workspace]\nmembers = ["libs/*"]\n')
        (self.project / "py/uv.lock").write_text("version = 1\n")
        (self.project / "py/libs/b/pyproject.toml").write_text('[project]\nname = "b"\ndependencies = ["requests"]\n')
        out = project_cmd(self.project, self.home, "code", "security", check=False).stdout
        self.assertNotIn("no lockfile", out, out)


@unittest.skipIf(not shutil.which("git"), "git not available")
class GitIgnoredSecrets(unittest.TestCase):
    def test_an_ignored_untracked_env_file_is_listed_not_gated(self):
        home = temp_home(self); project = home / "app"; project.mkdir(); install(home, project)
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)
        (project / ".gitignore").write_text(".env\n")
        (project / "backend").mkdir(); (project / "backend/.env").write_text("IQR_DATABASE_PASSWORD=2lu26men37dev9000\n")
        (project / "backend/config.env.production").write_text("DB_PASSWORD=2lu26men37dev9000\n")
        r = project_cmd(project, home, "code", "security", "--gate", check=False)
        self.assertIn("backend/.env:1  secret pattern", r.stdout, r.stdout)
        self.assertIn("[untracked, git-ignored]", r.stdout, r.stdout)
        self.assertIn("keep it ignored and ship a `.env.example`", r.stdout)
        self.assertIn("in tests, docs or git-ignored files (not gated", r.stdout, r.stdout)
        strict = project_cmd(project, home, "code", "security", "--gate", "--strict", check=False)
        self.assertEqual(strict.returncode, 1, "--strict gates it\n" + strict.stdout)


if __name__ == "__main__":
    unittest.main()
