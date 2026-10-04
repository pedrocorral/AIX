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
    "src/main/java/com/a/OrderController.java": """package com.a;
@RestController
public class OrderController {
  private final OrderService service = null;
  @GetMapping("/orders")
  public String find(@RequestParam("q") String q, @RequestParam int page) {
    String safe = Integer.toString(page);
    service.search(q, page);
    service.search(safe, page);
    service.count(q);
    return "";
  }
}
""",
    "src/main/java/com/a/OrderService.java": """package com.a;
public class OrderService {
  public List<Order> search(String term, int page) {
    return jdbc.queryForList("SELECT * FROM orders WHERE name = '" + term + "' LIMIT " + page);
  }
  public int count(String term, int extra) {
    return jdbc.queryForObject("SELECT count(*) FROM orders WHERE name = '" + term + "'", Integer.class);
  }
}
""",
    "src/main/java/com/a/Flows.java": """package com.a;
public class Flows extends HttpServlet {
  public void doPost(HttpServletRequest request, HttpServletResponse response) {
    String param = "";
    if (request.getHeader("X-Name") != null) {
      param = request.getHeader("X-Name");
    }
    java.io.PrintWriter out = response.getWriter();
    out.println(param);
    String bar;
    if (param.length() > 3) bar = param;
    else bar = "constant";
    java.util.List<String> argList = new java.util.ArrayList<String>();
    argList.add("ls");
    argList.add(bar);
    java.lang.ProcessBuilder pb = new java.lang.ProcessBuilder(argList);
    String fileName = "";
    fileName += param;
    java.io.FileInputStream fis = new java.io.FileInputStream(new java.io.File(fileName));
    javax.servlet.http.HttpSession session = request.getSession();
    session.setAttribute("name", param);
    String filter = "(uid=" + param + ")";
    ctx.search("ou=people", filter, sc);
    String expr = "/users/user[@name='" + param + "']";
    xp.evaluate(expr, doc);
    java.util.Random r = new java.util.Random();
    javax.crypto.Cipher c = javax.crypto.Cipher.getInstance("DES/CBC/PKCS5PADDING");
    cookie.setSecure(false);
  }
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

    def test_across_files_by_name_and_arity(self):
        """A controller's parameter reaches a service's SQL in another file: the callee is found through the receiver's
        type (or by name and arity when the type cannot be read) and walked once; `count(q)` has one argument and
        `count(String, int)` two, so it is not followed."""
        self.assertEqual(self.hits("OrderService.java"), [(4, "SQL statement")], self.out)
        self.assertRegex(self.out, r"OrderService\.java:4 .*\n.*argument of (?:OrderService\.)?search in src/main/java/com/a/OrderService\.java: (?:argument of \w+: )?q: @RequestParam")

    def test_flows_the_benchmark_uses(self):
        """A reassignment inside a block keeps the taint after it; a one-line `if` or `else` branch adds taint and
        never clears it; a tainted collection taints the ProcessBuilder it feeds; `+=` assembles; a writer variable
        and a session variable are sinks; qualified names; LDAP and XPath filters; `.exec` on a Runtime variable."""
        self.assertEqual(self.hits("Flows.java"), [(9, "HTML response"), (16, "shell command"), (19, "file path"), (21, "session attribute"), (23, "LDAP query"), (25, "XPath query")], self.out)

    def test_java_rules_from_the_benchmark(self):
        out = project_cmd(self.project, self.home, "code", "security", "src/main").stdout
        for title in ("non-cryptographic randomness", "weak or ECB cipher", "cookie marked not secure"):
            self.assertRegex(out, rf"Flows\.java:\d+  {title}", out)

    def test_tests_listed_not_gated_and_gate(self):
        self.assertRegex(self.out, r"SqlLessonTest\.java:3 .*\[test\]")
        r = project_cmd(self.project, self.home, "code", "vulnerabilities", "--taint", "--gate", "src", check=False)
        self.assertIn("GATE FAILED", r.stdout + r.stderr)
        r = project_cmd(self.project, self.home, "code", "vulnerabilities", "--taint", "--gate", "src/test", check=False)
        self.assertIn("GATE PASSED", r.stdout)


if __name__ == "__main__":
    unittest.main()
