"""1. The checkout itself: install, doctor, validate, the graph gate on the scripts, the built-in selftests."""
import unittest
from helpers import KIT, run, temp_home


class KitSelfChecks(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)

    def test_install_doctor_validate(self):
        run(["install"], cwd=KIT, home=self.home)
        d = run(["doctor"], cwd=KIT, home=self.home)
        self.assertIn("installation healthy", d.stdout)
        v = run(["docs", "validate"], cwd=KIT, home=self.home)
        self.assertIn("0 errors", v.stdout)

    def test_scripts_pass_the_graph_gate(self):
        r = run(["code", "graph", ".aix/scripts", "--gate"], cwd=KIT, home=self.home, check=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("GATE PASSED", r.stdout)

    def test_selftests(self):
        for tool in (["code", "graph"], ["code", "style"], ["code", "stats"]):
            r = run([*tool, "--selftest"], cwd=KIT, home=self.home, check=False)
            self.assertEqual(r.returncode, 0, f"{' '.join(tool)} --selftest\n{r.stdout}{r.stderr}")

    def test_guide(self):
        toc = run(["guide"], cwd=KIT, home=self.home).stdout
        for key in ("start", "concepts", "install", "agents", "skills", "instructions", "organisation", "docs", "code", "maintain", "reference"):
            self.assertIn(key, toc)
        one = run(["guide", "skills"], cwd=KIT, home=self.home).stdout
        self.assertIn("# 5. Skills", one)
        self.assertNotIn("id: META-GUIDE", one, "front matter is stripped")
        self.assertEqual(run(["guide", "5"], cwd=KIT, home=self.home).stdout, one)
        everything = run(["guide", "--all"], cwd=KIT, home=self.home).stdout
        self.assertIn("# 1. Start here", everything)
        self.assertIn("# 11. Command reference", everything)
        r = run(["guide", "nope"], cwd=KIT, home=self.home, check=False)
        self.assertNotEqual(r.returncode, 0)
        project = self.home / "app"
        from helpers import install, project_cmd
        install(self.home, project)
        self.assertIn("# 4. Agents", project_cmd(project, self.home, "guide", "agents").stdout, "the guide travels with the project")

    def test_help_and_version(self):
        self.assertIn("AIX", run(["version"], cwd=KIT, home=self.home).stdout)
        for topic in ("install", "upgrade", "instructions", "profile", "code find", "skills"):
            self.assertIn("aix", run(["help", topic], cwd=KIT, home=self.home).stdout, topic)


if __name__ == "__main__":
    unittest.main()
