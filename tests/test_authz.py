"""VUL-AUTHZ-001: a handler that takes an id from the URL and reaches a user-owned thing without tying it to the
caller (authz.py). One controller per situation: the bare handler is the finding; a security annotation, a principal
parameter, a current-user read in the service it calls, an owner-aware repository method, a thing without an owner,
and a project without authentication are not."""
import unittest

from helpers import install, project_cmd, temp_home

POM = '<project><dependencies><dependency><artifactId>spring-boot-starter-security</artifactId></dependency></dependencies></project>\n'
ACCOUNT = """package app;
@Entity
public class Account {
  private Long id;
  private User user;
}
"""
LABEL = """package app;
@Entity
public class Label {
  private Long id;
  private String name;
}
"""
SERVICE = """package app;
public class AccountService {
  public Account forCurrentUser(Long id) {
    String login = SecurityUtils.getCurrentUserLogin();
    return accountRepository.findByIdAndUserLogin(id, login);
  }
  public Account plain(Long id) {
    return accountRepository.findById(id).orElseThrow();
  }
}
"""
CONTROLLER = """package app;
@RestController
public class AccountResource {
  @GetMapping("/accounts/{id}")
  public ResponseEntity<Account> bare(@PathVariable("id") Long id) {
    return ResponseEntity.of(accountRepository.findById(id));
  }
  @GetMapping("/accounts/{id}/annotated")
  @PreAuthorize("hasRole('ADMIN')")
  public ResponseEntity<Account> annotated(@PathVariable("id") Long id) {
    return ResponseEntity.of(accountRepository.findById(id));
  }
  @GetMapping("/accounts/{id}/principal")
  public ResponseEntity<Account> withPrincipal(@PathVariable("id") Long id, Principal principal) {
    Account a = accountRepository.findById(id).orElseThrow();
    if (!a.getUser().getLogin().equals(principal.getName())) throw new AccessDeniedException("no");
    return ResponseEntity.ok(a);
  }
  @GetMapping("/accounts/{id}/service")
  public ResponseEntity<Account> throughService(@PathVariable("id") Long id) {
    return ResponseEntity.ok(accountService.forCurrentUser(id));
  }
  @GetMapping("/accounts/{id}/plain-service")
  public ResponseEntity<Account> throughPlainService(@PathVariable("id") Long id) {
    return ResponseEntity.ok(accountService.plain(id));
  }
  @DeleteMapping("/accounts/{id}")
  public void remove(@PathVariable("id") Long id) {
    accountRepository.deleteByIdAndUserLogin(id, SecurityUtils.getCurrentUserLogin());
  }
  @GetMapping("/labels/{id}")
  public ResponseEntity<Label> label(@PathVariable("id") Long id) {
    return ResponseEntity.of(labelRepository.findById(id));
  }
}
"""


def write(project, with_security: bool):
    src = project / "src/main/java/app"; src.mkdir(parents=True)
    (src / "Account.java").write_text(ACCOUNT); (src / "Label.java").write_text(LABEL)
    (src / "AccountService.java").write_text(SERVICE); (src / "AccountResource.java").write_text(CONTROLLER)
    if with_security:
        (project / "pom.xml").write_text(POM)


class OwnershipChecks(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        write(self.project, True)
        install(self.home, self.project)
        self.out = project_cmd(self.project, self.home, "code", "security", "src", check=False).stdout

    def findings(self) -> list:
        return sorted(int(l.split("AccountResource.java:")[1].split()[0]) for l in self.out.splitlines() if "CWE-639" in l)

    def test_only_the_handlers_without_a_check_are_reported(self):
        self.assertEqual(self.findings(), [5, 24], self.out)   # bare, and the service that loads by id alone
        self.assertIn("reaches a user-owned Account", self.out)

    def test_the_row_is_listed_as_ruled(self):
        self.assertIn("VUL-AUTHZ-001", self.out)


class NoAuthentication(unittest.TestCase):
    def test_nothing_without_logins(self):
        home = temp_home(self); project = home / "app"
        write(project, False)
        install(home, project)
        out = project_cmd(project, home, "code", "security", "src", check=False).stdout
        self.assertNotIn("CWE-639", out, out)
        self.assertIn("VUL-AUTHZ-001", out, "the row still counts as ruled: no pattern matched")


if __name__ == "__main__":
    unittest.main()
