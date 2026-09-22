"""10. aix self-install: the link in ~/.local/bin, the PATH line in the shell profiles, idempotence, foreign files,
stale links, dry run, refusal from a project's copy, the `install aix` alias, `aix version` inside a project."""
import os, unittest
from helpers import KIT, LAUNCHER, LAUNCHER_NAME, install, run, temp_home

BASH = {"SHELL": "/bin/bash"}


@unittest.skipIf(os.name == "nt", "POSIX link and profile logic; Windows is covered by CI once it runs there")
class SelfInstall(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.bin = self.home / ".local" / "bin"
        self.link = self.bin / "aix"

    def test_creates_link_and_profile_line(self):
        (self.home / ".bashrc").write_text("# my rc\n", encoding="utf-8")
        r = run(["self-install"], cwd=KIT, home=self.home, extra_env=BASH)
        self.assertTrue(self.link.is_symlink() and self.link.resolve() == LAUNCHER.resolve(), r.stdout)
        rc = (self.home / ".bashrc").read_text(encoding="utf-8")
        self.assertIn("# added by aix self-install", rc)
        self.assertIn('export PATH="$HOME/.local/bin:$PATH"', rc)
        self.assertIn("PATH changed: open a new terminal", r.stdout)
        self.assertIn("verify  `aix version` -> AIX", r.stdout)

    def test_idempotent(self):
        run(["self-install"], cwd=KIT, home=self.home, extra_env=BASH)
        r = run(["self-install"], cwd=KIT, home=self.home, extra_env=BASH)
        self.assertIn("already points to this clone", r.stdout)
        self.assertIn("already has the line", r.stdout)
        self.assertEqual((self.home / ".bashrc").read_text(encoding="utf-8").count("added by aix self-install"), 1)

    def test_every_shell_profile_found_gets_the_line(self):
        (self.home / ".zshrc").write_text("", encoding="utf-8")
        (self.home / ".config" / "fish").mkdir(parents=True)
        (self.home / ".config" / "fish" / "config.fish").write_text("", encoding="utf-8")
        run(["self-install"], cwd=KIT, home=self.home, extra_env={"SHELL": "/usr/bin/zsh"})
        self.assertIn("export PATH", (self.home / ".zshrc").read_text(encoding="utf-8"))
        self.assertIn("fish_add_path -g $HOME/.local/bin", (self.home / ".config" / "fish" / "config.fish").read_text(encoding="utf-8"))
        self.assertFalse((self.home / ".bashrc").exists(), "no bash profile is invented for a zsh user")

    def test_no_profile_edit_when_already_on_path(self):
        self.bin.mkdir(parents=True)
        (self.home / ".bashrc").write_text("# rc\n", encoding="utf-8")
        r = run(["self-install"], cwd=KIT, home=self.home, extra_env={**BASH, "PATH": f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}"})
        self.assertIn("is already on PATH", r.stdout)
        self.assertNotIn("aix self-install", (self.home / ".bashrc").read_text(encoding="utf-8"))
        self.assertIn("`aix` works from any terminal", r.stdout)

    def test_foreign_file_is_kept_and_stale_link_replaced(self):
        self.bin.mkdir(parents=True)
        self.link.write_text("#!/bin/sh\necho other tool\n", encoding="utf-8")
        r = run(["self-install", "--no-profile"], cwd=KIT, home=self.home, extra_env=BASH)
        self.assertIn("moved to", r.stdout)
        self.assertTrue((self.bin / "aix.bak").exists())
        self.assertTrue(self.link.is_symlink())
        self.link.unlink()
        self.link.symlink_to(self.home / "nowhere" / "aix")
        r = run(["self-install", "--no-profile"], cwd=KIT, home=self.home, extra_env=BASH)
        self.assertIn("pointed elsewhere", r.stdout)
        self.assertEqual(self.link.resolve(), LAUNCHER.resolve())

    def test_dry_run_writes_nothing(self):
        (self.home / ".bashrc").write_text("# rc\n", encoding="utf-8")
        r = run(["self-install", "--dry-run"], cwd=KIT, home=self.home, extra_env=BASH)
        self.assertIn("dry run", r.stdout)
        self.assertIn("mkdir", r.stdout)
        self.assertFalse(self.bin.exists())
        self.assertEqual((self.home / ".bashrc").read_text(encoding="utf-8"), "# rc\n")

    def test_install_aix_alias_and_refusal_from_a_project(self):
        r = run(["install", "aix", "--dry-run"], cwd=KIT, home=self.home, extra_env=BASH)
        self.assertIn("aix self-install", r.stdout)
        project = self.home / "app"
        install(self.home, project)
        r = run(["self-install"], cwd=project, home=self.home, launcher=project / ".aix" / "bin" / LAUNCHER_NAME, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("project's copy", r.stdout + r.stderr)

    def test_version_inside_a_project_names_both_copies(self):
        run(["self-install", "--no-profile"], cwd=KIT, home=self.home, extra_env=BASH)
        project = self.home / "app"
        install(self.home, project)
        path = f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}"
        r = run(["version"], cwd=project, home=self.home, extra_env={"PATH": path})
        self.assertIn("(this project's copy)", r.stdout)
        self.assertIn("kit on PATH:", r.stdout)
        self.assertNotIn("aix upgrade", r.stdout, "same version: no hint")
        cfg = project / ".aix" / "config.yaml"
        cfg.write_text(cfg.read_text(encoding="utf-8").replace("version: ", "version: 0.", 1), encoding="utf-8")
        r = run(["version"], cwd=project, home=self.home, extra_env={"PATH": path})
        self.assertIn("run `aix upgrade`", r.stdout)


if __name__ == "__main__":
    unittest.main()
