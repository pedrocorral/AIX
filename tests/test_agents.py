"""11. aix agents: the fixed list, names and aliases, only the selected agents' folders and pointer files, deselection
removes AIX files and keeps a person's, --agents at install, upgrade keeps the line, the checklist through a pty."""
import os, re, unittest
from helpers import KIT, LAUNCHER, assert_healthy, config, env, install, previous_kit, project_cmd, run, temp_home, upgrade

FILES = {"claude": [".claude/skills/core-sdd-workflow", "CLAUDE.md"], "copilot": [".github/skills/core-sdd-workflow", ".github/copilot-instructions.md"],
         "cursor": [".cursor/skills/core-sdd-workflow", ".cursor/rules/aix.mdc"], "gemini": [".agents/skills/core-sdd-workflow", "GEMINI.md"],
         "opencode": [".opencode/skills/core-sdd-workflow"]}


def present(project, agent):
    return [f for f in FILES[agent] if (project / f).exists()]


class AgentsSelection(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        install(self.home, self.project)

    def test_default_is_all_and_list_changes_nothing(self):
        for agent in FILES:
            self.assertEqual(present(self.project, agent), FILES[agent], agent)
        out = project_cmd(self.project, self.home, "agents", "--list").stdout
        for name in ("claude", "copilot", "cursor", "gemini", "opencode", "codex"):
            self.assertIn(name, out)
        self.assertIn("all (no agents: line)", out)
        self.assertNotRegex(config(self.project), r"(?m)^agents:")

    def test_names_select_and_deselection_removes_aix_files(self):
        r = project_cmd(self.project, self.home, "agents", "claude", "vscode")
        self.assertIn("agents: ['claude', 'copilot']", r.stdout, "vscode is an alias of copilot")
        self.assertRegex(config(self.project), r"(?m)^agents: \[claude, copilot\]")
        for agent in ("claude", "copilot"):
            self.assertEqual(present(self.project, agent), FILES[agent], agent)
        for agent in ("cursor", "gemini", "opencode"):
            self.assertEqual(present(self.project, agent), [], f"{agent} files must be gone")
        self.assertFalse((self.project / ".cursor").exists(), "empty folders are removed")
        self.assertTrue((self.project / "AGENTS.md").exists())
        doctor = assert_healthy(self, self.project, self.home)
        self.assertIn("agents: claude, copilot", doctor)
        self.assertIn("for claude, copilot", project_cmd(self.project, self.home, "install").stdout)

    def test_a_persons_pointer_file_is_never_removed(self):
        gem = self.project / "GEMINI.md"
        gem.write_text("My own Gemini notes.\n", encoding="utf-8")
        project_cmd(self.project, self.home, "agents", "claude")
        self.assertTrue(gem.exists())
        self.assertEqual(gem.read_text(encoding="utf-8"), "My own Gemini notes.\n")
        self.assertFalse((self.project / ".agents").exists(), "the links go, the person's file stays")

    def test_all_restores_everything(self):
        project_cmd(self.project, self.home, "agents", "cursor")
        project_cmd(self.project, self.home, "agents", "all")
        self.assertNotRegex(config(self.project), r"(?m)^agents:")
        for agent in FILES:
            self.assertEqual(present(self.project, agent), FILES[agent], agent)
        assert_healthy(self, self.project, self.home)

    def test_rendered_instructions_follow_the_selection(self):
        project_cmd(self.project, self.home, "agents", "cursor")
        project_cmd(self.project, self.home, "instructions", "enable", "aix/languages/rust")
        self.assertTrue((self.project / ".cursor" / "rules" / "aix-languages-rust.mdc").exists())
        self.assertFalse((self.project / ".github" / "instructions").exists(), "no Copilot files for a Cursor-only project")
        project_cmd(self.project, self.home, "agents", "copilot")
        self.assertTrue((self.project / ".github" / "instructions" / "aix-languages-rust.instructions.md").exists())
        self.assertFalse((self.project / ".cursor").exists())
        assert_healthy(self, self.project, self.home)

    def test_skills_commands_respect_the_selection(self):
        project_cmd(self.project, self.home, "agents", "claude")
        project_cmd(self.project, self.home, "skills", "disable", "core-find-doc")
        project_cmd(self.project, self.home, "skills", "enable", "core-find-doc")
        self.assertTrue((self.project / ".claude" / "skills" / "core-find-doc").exists())
        self.assertFalse((self.project / ".github").exists())
        info = project_cmd(self.project, self.home, "skills", "info", "core-find-doc").stdout
        self.assertIn("installed:   claude", info)

    def test_unknown_name_fails(self):
        r = project_cmd(self.project, self.home, "agents", "emacs", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown agent", r.stdout + r.stderr)


class AgentsAtInstallAndUpgrade(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)

    def test_install_with_agents_flag(self):
        project = self.home / "app"
        r = install(self.home, project, "--agents", "cursor,opencode")
        self.assertIn("for cursor, opencode", r.stdout)
        self.assertRegex(config(project), r"(?m)^agents: \[cursor, opencode\]")
        for agent in ("claude", "copilot", "gemini"):
            self.assertEqual(present(project, agent), [], agent)
        self.assertFalse((project / "CLAUDE.md").exists() or (project / "GEMINI.md").exists())
        assert_healthy(self, project, self.home)

    def test_install_without_terminal_equips_all_and_says_so(self):
        project = self.home / "app"
        r = install(self.home, project)
        self.assertIn("no terminal to ask: all agents are equipped", r.stdout)
        self.assertTrue((project / "GEMINI.md").exists())

    def test_upgrade_keeps_the_selection_and_adds_no_pointer_back(self):
        prev = previous_kit(self, self.home)
        project = self.home / "app"
        install(self.home, project, kit=prev)
        upgrade(project, self.home)  # first: bring the CLI to this version
        project_cmd(project, self.home, "agents", "claude")
        self.assertFalse((project / "GEMINI.md").exists())
        upgrade(project, self.home)
        self.assertRegex(config(project), r"(?m)^agents: \[claude\]")
        self.assertFalse((project / "GEMINI.md").exists(), "upgrade must not re-add a deselected agent's pointer")
        self.assertTrue((project / "CLAUDE.md").exists())
        assert_healthy(self, project, self.home)

    @unittest.skipIf(os.name == "nt", "curses checklist: Linux/macOS only")
    def test_checklist_through_a_pseudo_terminal(self):
        """Select all (a), untick the first row (claude), apply: agents = everything but claude."""
        import pty, select, time
        project = self.home / "app"
        install(self.home, project)
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(project)
            e = env(self.home); e.pop("CI", None); e.update({"LINES": "24", "COLUMNS": "120"})
            os.execve(str(LAUNCHER), [str(LAUNCHER), "agents"], e)
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
        read(1.5)
        for key in (b"a", b" ", b"\r"):
            os.write(fd, key); read(0.5)
        read(2.0)
        self.assertIn(b"add them to .gitignore? [y/N]", out, "the .gitignore question follows the selection")
        os.write(fd, b"n\n"); read(1.5)
        os.waitpid(pid, 0)
        plain = re.sub(rb"\x1b\[[0-9;?]*[A-Za-z]", b"", out).decode(errors="replace")
        self.assertIn("which agents does this project equip", plain)
        self.assertRegex(config(project), r"(?m)^agents: \[copilot, cursor, gemini, opencode, codex\]")
        self.assertFalse((project / "CLAUDE.md").exists())
        self.assertFalse((project / ".gitignore").exists(), "answered n")


if __name__ == "__main__":
    unittest.main()
