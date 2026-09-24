"""18. Java: the code tools on a small Maven project (two packages, a wildcard import, a JUnit test, a SQL string built
two lines before it runs). Same-package and wildcard references are edges, entry classes are not dead, the two-line
SQL shape is a finding."""
import unittest
from helpers import fixture, install, project_cmd, temp_home


class JavaProject(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = fixture("java-app", self.home / "java-app")
        install(self.home, self.project)
        project_cmd(self.project, self.home, "code", "find", "--yes")

    def test_references_without_a_class_import_are_edges(self):
        out = project_cmd(self.project, self.home, "code", "graph").stdout
        self.assertIn("nodes 5, edges 4", out, "Main->Service, Service->Repo (same package), Main->Text (wildcard), ServiceTest->Service\n" + out)
        self.assertIn("cycles 0   upward dependencies 0", out)

    def test_nothing_is_dead(self):
        out = project_cmd(self.project, self.home, "code", "dead").stdout
        self.assertIn("DEAD MODULES 0", out, out)
        self.assertIn("Main.java", out, "the class with main is an entry module")

    def test_sql_built_two_lines_before_it_runs(self):
        r = project_cmd(self.project, self.home, "code", "security", "--gate", check=False)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("Repo.java:6", r.stdout)
        self.assertIn("VUL-INJ-001", r.stdout)
        self.assertIn("SELECT * FROM t WHERE id = \" + id", r.stdout, "the snippet shows the assembled string")

    def test_runtime_and_style(self):
        out = project_cmd(self.project, self.home, "code", "style").stdout
        self.assertIn("runtime: Java 17 (pom.xml)", out)
        self.assertIn("functions analysed 5", out)
        self.assertIn("switch expression", out, "modernise advice for Java 14+")


if __name__ == "__main__":
    unittest.main()
