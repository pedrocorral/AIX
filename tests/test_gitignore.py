"""12. .gitignore and backups: the missing AIX lines are printed without a terminal and touched only on a yes
(`upgrade --yes`, or a y answer through a pseudo-terminal), added once; a person's file where AIX writes is kept as -bak."""
import os, re, unittest
from helpers import LAUNCHER, env, install, project_cmd, temp_home, upgrade


def gitignore(project):
    p = project / ".gitignore"
    return p.read_text(encoding="utf-8") if p.exists() else ""


class GitignoreLines(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"

    def test_install_without_terminal_prints_and_touches_nothing(self):
        r = install(self.home, self.project)
        self.assertIn(".gitignore (new file) lacks", r.stdout)
        self.assertIn("    .aix/", r.stdout)
        self.assertIn("    .claude/skills/", r.stdout)
        self.assertIn("no terminal to ask", r.stdout)
        self.assertFalse((self.project / ".gitignore").exists())

    def test_upgrade_yes_adds_them_once_and_respects_the_selection(self):
        install(self.home, self.project, "--agents", "claude,cursor")
        r = upgrade(self.project, self.home)
        self.assertIn("added", r.stdout)
        text = gitignore(self.project)
        for line in (".aix/", ".claude/skills/", ".cursor/skills/", ".cursor/rules/aix-*", "docs/tests/coverage-matrix.md"):
            self.assertIn(line + "\n", text, line)
        self.assertNotIn(".github/skills/", text, "copilot is not selected")
        self.assertNotIn(".agents/skills/", text)
        r = upgrade(self.project, self.home)
        self.assertNotIn("lacks", r.stdout, "second run: nothing missing")
        self.assertEqual(text, gitignore(self.project))
        self.assertEqual(gitignore(self.project).count("# AIX:"), 1)

    def test_existing_lines_are_kept_and_not_duplicated(self):
        install(self.home, self.project, "--agents", "claude")
        (self.project / ".gitignore").write_text("node_modules/\n.aix\n.claude/skills/\n", encoding="utf-8")
        r = upgrade(self.project, self.home)
        text = gitignore(self.project)
        self.assertTrue(text.startswith("node_modules/\n.aix\n.claude/skills/\n"), "a person's lines are untouched")
        self.assertEqual(text.count(".claude/skills/"), 1, ".aix and .claude/skills were already there (trailing slash or not)")
        self.assertIn("docs/tests/code-style.md\n", text)

    @unittest.skipIf(os.name == "nt", "pseudo-terminal: Linux/macOS only")
    def test_agents_asks_and_a_y_answer_writes(self):
        install(self.home, self.project)
        import pty, select, time
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(self.project)
            e = env(self.home); e.pop("CI", None)
            os.execve(str(LAUNCHER), [str(LAUNCHER), "agents", "claude"], e)
        out = b""
        def read(seconds):
            nonlocal out
            end = time.time() + seconds
            while time.time() < end:
                r, _, _ = select.select([fd], [], [], 0.1)
                if r:
                    try:
                        out += os.read(fd, 65536)
                    except OSError:
                        return
        read(2.0)
        self.assertIn(b"add them to .gitignore? [y/N]", out)
        os.write(fd, b"y\n"); read(1.5)
        os.waitpid(pid, 0)
        text = gitignore(self.project)
        self.assertIn(".aix/\n", text)
        self.assertIn(".claude/skills/\n", text)
        self.assertNotIn(".github/skills/", text)


class Backups(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"

    def test_a_persons_pointer_and_skills_folder_are_kept_as_bak(self):
        self.project.mkdir()
        (self.project / "CLAUDE.md").write_text("My own Claude notes.\n", encoding="utf-8")
        (self.project / ".github" / "skills" / "mine").mkdir(parents=True)
        (self.project / ".github" / "skills" / "mine" / "SKILL.md").write_text("---\nname: mine\ndescription: a hand-made skill\n---\n", encoding="utf-8")
        (self.project / ".github" / "workflows").mkdir()
        (self.project / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
        r = install(self.home, self.project, "--agents", "claude,copilot", "--merge-all")
        self.assertIn("CLAUDE.md was not AIX's: kept as CLAUDE.md-bak", r.stdout)
        self.assertIn(".github/skills was not AIX's: kept as .github/skills-bak", r.stdout)
        self.assertEqual((self.project / "CLAUDE.md-bak").read_text(encoding="utf-8"), "My own Claude notes.\n")
        self.assertIn("Read and follow `AGENTS.md`", (self.project / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertTrue((self.project / ".github" / "skills-bak" / "mine" / "SKILL.md").exists())
        self.assertTrue((self.project / ".github" / "skills" / "core-sdd-workflow").exists())
        self.assertTrue((self.project / ".github" / "workflows" / "ci.yml").exists(), "never the parent folder")
        r = project_cmd(self.project, self.home, "install")
        self.assertNotIn("kept as", r.stdout, "AIX's own files are recognised on the next run")


if __name__ == "__main__":
    unittest.main()
