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

    def test_help_and_version(self):
        self.assertIn("AIX", run(["version"], cwd=KIT, home=self.home).stdout)
        for topic in ("install", "upgrade", "instructions", "profile", "code find", "skills"):
            self.assertIn("aix", run(["help", topic], cwd=KIT, home=self.home).stdout, topic)


if __name__ == "__main__":
    unittest.main()
