"""Java sinks after the CodeQL benchmark (section 18): a whole tainted statement handed to `executeQuery` is a finding
(raw, not only assembled); a parameterised `jdbcTemplate.update(sql, params)` with the tainted value among the
parameters is not; `super.execute(file, name)` is not a JDBC sink; `xstream.fromXML(payload)` on a variable is a
deserialisation sink; a tainted document into an XML parser is an XXE finding; a JSON parser is not."""
import unittest

from helpers import install, project_cmd, temp_home

SAMPLE = """package app;
@RestController
public class Sinks {
  @PostMapping("/raw")
  public String raw(@RequestParam String query) throws Exception {
    Statement statement = connection.createStatement();
    ResultSet results = statement.executeQuery(query);
    return results.toString();
  }
  @PostMapping("/params")
  public void params(@RequestParam String username) {
    jdbcTemplate.update("INSERT INTO users(username) VALUES(:username)", new MapSqlParameterSource().addValue("username", username));
  }
  @PostMapping("/assembled")
  public void assembled(@RequestParam String username) {
    jdbcTemplate.update("INSERT INTO users(username) VALUES('" + username + "')");
  }
  @PostMapping("/upload")
  public String upload(@RequestParam("file") MultipartFile file, @RequestParam String fullName) {
    return super.execute(file, fullName);
  }
  @PostMapping("/xml")
  public Object xml(@RequestBody String payload) throws Exception {
    Object thing = xstream.fromXML(payload);
    XMLStreamReader reader = xif.createXMLStreamReader(new StringReader(payload));
    JsonNode node = jsonParser.parse(payload);
    return thing;
  }
}
"""


class JavaSinks(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        src = self.project / "src/main/java/app"; src.mkdir(parents=True)
        (src / "Sinks.java").write_text(SAMPLE, encoding="utf-8")
        install(self.home, self.project)
        self.out = project_cmd(self.project, self.home, "code", "vulnerabilities", "--taint", check=False).stdout

    def hits(self) -> list:
        return sorted((int(l.split("Sinks.java:")[1].split()[0]), l.split("input reaches ")[1].split(" (")[0]) for l in self.out.splitlines() if "Sinks.java:" in l and "input reaches" in l)

    def test_sinks(self):
        self.assertEqual(self.hits(), [(7, "SQL statement"), (16, "SQL statement"), (24, "deserialisation"), (25, "XML document parsed")], self.out)


if __name__ == "__main__":
    unittest.main()
