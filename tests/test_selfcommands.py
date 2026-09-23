"""13. The self-* family and the installer: aix self-update against a local origin, aix self-test on one file,
install.sh end to end with a local repository, and doctor's warning about a deselected agent's leftovers."""
import os, shutil, subprocess, unittest
from helpers import KIT, LAUNCHER_NAME, env, install, project_cmd, run, temp_home


def git(cwd, *args, home):
    return subprocess.run(["git", "-C", str(cwd), *args], env=env(home), capture_output=True, text=True, check=True)


class SelfUpdateUnits(unittest.TestCase):
    """The pieces of self-update, each on its own (no launcher, no network)."""
    def setUp(self):
        import sys
        sys.path.insert(0, str(KIT / ".aix" / "scripts"))
        import selfinstall
        self.si = selfinstall
        self.home = temp_home(self)

    def test_is_git_clone(self):
        self.assertTrue(self.si.is_git_clone(KIT))
        copy = self.home / "copy"; copy.mkdir()
        self.assertFalse(self.si.is_git_clone(copy))

    def test_version_of(self):
        k = self.home / "k"; (k / ".aix").mkdir(parents=True)
        (k / ".aix" / "config.yaml").write_text("name: aix\nversion: 3.4.5   # comment\n", encoding="utf-8")
        self.assertEqual(self.si.version_of(k), "3.4.5")

    def test_update_message(self):
        k = self.home / "k"
        self.assertTrue(self.si.update_message(k, "2.0.0", "2.0.0").endswith("(already current)"))
        msg = self.si.update_message(k, "2.0.0", "2.1.0")
        self.assertIn("2.0.0 -> 2.1.0", msg)
        self.assertIn("run `aix upgrade` inside each project", msg)

    @unittest.skipIf(not shutil.which("git"), "git not available")
    def test_git_pull_ok_and_failure(self):
        origin = self.home / "o.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(KIT), str(origin)], env=env(self.home), check=True, capture_output=True)
        clone = self.home / "c"
        subprocess.run(["git", "clone", "-q", str(origin), str(clone)], env=env(self.home), check=True, capture_output=True)
        os.environ.update({k: v for k, v in env(self.home).items() if k.startswith("GIT_CONFIG")})
        ok, msg = self.si.git_pull(clone)
        self.assertTrue(ok, msg)
        subprocess.run(["git", "-C", str(clone), "remote", "set-url", "origin", str(self.home / "nowhere")], env=env(self.home), check=True)
        ok, msg = self.si.git_pull(clone)
        self.assertFalse(ok)
        self.assertTrue(msg, "a failure carries git's message")


@unittest.skipIf(not shutil.which("git"), "git not available")
class SelfUpdate(unittest.TestCase):
    def test_pulls_the_origin_and_reports_the_versions(self):
        home = temp_home(self)
        origin = home / "origin.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(KIT), str(origin)], env=env(home), check=True, capture_output=True)
        clone = home / "clone"
        subprocess.run(["git", "clone", "-q", str(origin), str(clone)], env=env(home), check=True, capture_output=True)
        launcher = clone / ".aix" / "bin" / LAUNCHER_NAME
        r = run(["self-update"], cwd=clone, home=home, launcher=launcher)
        self.assertIn("(already current)", r.stdout)
        # a newer version lands on the origin: bump it from a second clone and push
        other = home / "other"
        subprocess.run(["git", "clone", "-q", str(origin), str(other)], env=env(home), check=True, capture_output=True)
        cfg = other / ".aix" / "config.yaml"
        cfg.write_text(cfg.read_text(encoding="utf-8").replace("version: ", "version: 9", 1), encoding="utf-8")
        git(other, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "bump", home=home)
        git(other, "push", "-q", home=home)
        r = run(["self-update"], cwd=clone, home=home, launcher=launcher)
        self.assertIn("-> 9", r.stdout)
        self.assertIn("run `aix upgrade` inside each project", r.stdout)

    def test_refuses_outside_a_git_clone(self):
        home = temp_home(self)
        copy = home / "copy"
        shutil.copytree(KIT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".claude", ".github", ".cursor", ".agents", ".opencode"))
        r = run(["self-update"], cwd=copy, home=home, launcher=copy / ".aix" / "bin" / LAUNCHER_NAME, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not a git checkout", r.stdout + r.stderr)


class SelfTest(unittest.TestCase):
    def test_runs_one_file_and_refuses_from_a_project(self):
        home = temp_home(self)
        r = run(["self-test", "kit", "-q"], cwd=KIT, home=home, extra_env={"AIX_SELFTEST_NESTED": "1"})
        self.assertIn("OK", r.stderr + r.stdout)
        project = home / "app"
        install(home, project)
        r = run(["self-test"], cwd=project, home=home, launcher=project / ".aix" / "bin" / LAUNCHER_NAME, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("projects carry no tests", r.stdout + r.stderr)


@unittest.skipIf(os.name == "nt" or not shutil.which("git"), "sh installer: Linux/macOS with git")
class InstallSh(unittest.TestCase):
    def test_clones_a_local_repo_and_runs_self_install(self):
        home = temp_home(self)
        e = env(home)
        e.update({"AIX_REPO": str(KIT), "AIX_HOME": str(home / "kit"), "SHELL": "/bin/bash"})
        (home / ".bashrc").write_text("# rc\n", encoding="utf-8")
        r = subprocess.run(["sh", str(KIT / "install.sh")], env=e, capture_output=True, text=True, cwd=str(home))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("cloning", r.stdout)
        link = home / ".local" / "bin" / "aix"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), (home / "kit" / ".aix" / "bin" / "aix").resolve())
        self.assertIn("export PATH", (home / ".bashrc").read_text(encoding="utf-8"))
        r = subprocess.run(["sh", str(KIT / "install.sh")], env=e, capture_output=True, text=True, cwd=str(home))
        self.assertIn("updating", r.stdout, "second run pulls instead of cloning")
        self.assertIn("already points to this clone", r.stdout)


class DoctorLeftovers(unittest.TestCase):
    def test_warns_about_a_deselected_agents_files(self):
        home = temp_home(self)
        project = home / "app"
        install(home, project, "--agents", "claude")
        (project / ".cursor" / "skills").mkdir(parents=True)
        (project / ".cursor" / "skills" / "x").symlink_to(project / ".aix" / "skills" / "core" / "find-doc")
        d = project_cmd(project, home, "doctor", check=False)
        self.assertIn("cursor is not selected but AIX files remain", d.stdout)
        self.assertIn("aix agents", d.stdout)
        project_cmd(project, home, "agents", "claude")
        self.assertFalse((project / ".cursor").exists())
        self.assertIn("installation healthy", project_cmd(project, home, "doctor").stdout)


if __name__ == "__main__":
    unittest.main()
