"""Java taint (javataint.py on the shared walker): Spring binding annotations and servlet getters as sources,
JDBC, exec, file, redirect, deserialisation and outbound-request sinks, parseInt and escapers as sanitisers,
multi-line heads and assignments, one call deep into a method of the same file, PreparedStatement parameters
clean, the accepted marker, the tag and the gate."""
import unittest

from helpers import install, project_cmd, temp_home

SAMPLES = {
    "src/main/java/com/a/SqlLesson.java": """package com.a;
public class SqlLesson {
  @PostMapping("/attack")
  public AttackResult completed(
      @RequestParam String account, @RequestParam String operator) {
    return injectableQuery(account + " " + operator);
  }
  protected AttackResult injectableQuery(String accountName) {
    String query =
        "SELECT * FROM user_data WHERE last_name = '" + accountName + "'";
    try (Statement statement = connection.createStatement()) {
      ResultSet results = statement.executeQuery(query);
    }
    return null;
  }
  public void safe(@RequestParam String name) {
    PreparedStatement ps = connection.prepareStatement("SELECT * FROM t WHERE n = ?");
    ps.setString(1, name);
    ps.executeQuery();
  }
  public void numeric(@RequestParam String id) {
    int n = Integer.parseInt(id);
    statement.executeQuery("SELECT * FROM t WHERE id = " + n);
  }
}
""",
    "src/main/java/com/a/Servlet.java": """package com.a;
public class Servlet extends HttpServlet {
  protected void doGet(HttpServletRequest request, HttpServletResponse response) {
    String cmd = request.getParameter("cmd");
    Runtime.getRuntime().exec(cmd);
    String file = request.getParameter("f");
    File f = new File(base, file);
    response.sendRedirect(request.getParameter("next"));
    String ok = HtmlUtils.htmlEscape(request.getParameter("q"));
    response.getWriter().println(ok);
    response.getWriter().println(request.getParameter("raw"));
    String url = "http://x/" + request.getHeader("Host");
    new URL(url).openStream();
    ObjectInputStream in = new ObjectInputStream(request.getInputStream());   // aix: accepted VUL-INPUT-002 demo of the lesson
  }
  public static void main(String[] args) { }
}
""",
    "src/test/java/com/a/SqlLessonTest.java": """package com.a;
public class SqlLessonTest {
  void t(@RequestParam String x) { statement.executeQuery("SELECT " + x); }
}
""",
}


class JavaTaint(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        for name, src in SAMPLES.items():
            (self.project / name).parent.mkdir(parents=True, exist_ok=True)
            (self.project / name).write_text(src, encoding="utf-8")
        install(self.home, self.project)
        self.out = project_cmd(self.project, self.home, "code", "vulnerabilities", "--taint", "src").stdout

    def hits(self, file: str) -> list:
        import re
        return sorted((int(m.group(1)), m.group(2)) for m in re.finditer(rf"{re.escape(file)}:(\d+)  input reaches ([^(]+?) \(", self.out))

    def test_sql_one_call_deep_and_sanitisers(self):
        self.assertEqual(self.hits("SqlLesson.java"), [(12, "SQL statement")], self.out)   # through injectableQuery, the multi-line assignment; not the PreparedStatement, not the parsed int

    def test_servlet_sinks(self):
        self.assertEqual(self.hits("Servlet.java"), [(5, "shell command"), (7, "file path"), (8, "redirect target"), (11, "HTML response"), (13, "outbound request URL"), (14, "deserialisation")], self.out)
        self.assertRegex(self.out, r"Servlet\.java:14 .*\[accepted: demo of the lesson\]")

    def test_tests_listed_not_gated_and_gate(self):
        self.assertRegex(self.out, r"SqlLessonTest\.java:3 .*\[test\]")
        r = project_cmd(self.project, self.home, "code", "vulnerabilities", "--taint", "--gate", "src", check=False)
        self.assertIn("GATE FAILED", r.stdout + r.stderr)
        r = project_cmd(self.project, self.home, "code", "vulnerabilities", "--taint", "--gate", "src/test", check=False)
        self.assertIn("GATE PASSED", r.stdout)


if __name__ == "__main__":
    unittest.main()
