"""Every id and every reference to one is checked against the scheme (idcheck.py, `aix docs validate`): the shape of
its prefix, the domain code in the glossary, the file named after it, defined once, in front matter, in `covers:`
lists, in document text and in code markers. Agents invent shapes: each planted one is reported exactly once with the
rule it breaks; the valid ones are not."""
import unittest

from helpers import install, project_cmd, temp_home

GLOSSARY = "---\nid: PRODUCT-GLOSSARY\ntitle: Glossary\n---\n# Glossary\n\n| Term | Definition | Domain code |\n|---|---|---|\n| Auth | sign in | AUTH |\n| Billing | money | BILLING |\n"
DOCS = {
    "requirements/functional/auth/FR-AUTH-001-login.md": "---\nid: FR-AUTH-001\ntitle: Login\n---\n# Login\n",
    "tests/functional/auth/TS-AUTH-001-login-flow.md": "---\nid: TS-AUTH-001\ntitle: Login flow\ncovers: [FR-AUTH-001, VUL-WEB-002]\n---\n# Login flow\nSee FR-AUTH-001.\n",
    "tests/functional/auth/TS-VUL-WEB-002-csrf.md": "---\nid: TS-VUL-WEB-002\ntitle: CSRF\n---\n# CSRF\n",
    "tests/functional/auth/ts-auth-002-lower.md": "---\nid: ts-auth-002\ntitle: Lower\n---\n# Lower\n",
    "tests/functional/auth/TS-AUTH-7-short.md": "---\nid: TS-AUTH-7\ntitle: Short\n---\n# Short\n",
    "tests/functional/catalog/TS-CATALOG-001-browse.md": "---\nid: TS-CATALOG-001\ntitle: Browse\n---\n# Browse\n",
    "tests/functional/auth/TEST-AUTH-001-wrong-prefix.md": "---\nid: TEST-AUTH-001\ntitle: Wrong prefix\n---\n# Wrong prefix\n",
    "tests/functional/auth/misnamed.md": "---\nid: TS-AUTH-003\ntitle: Misnamed\n---\n# Misnamed\n",
    "tests/functional/auth/TS-AUTH-004-twice.md": "---\nid: TS-AUTH-004\ntitle: Twice\n---\n# Twice\n",
    "tests/functional/billing/TS-AUTH-004-again.md": "---\nid: TS-AUTH-004\ntitle: Again\n---\n# Again\n",
    "tests/functional/billing/TS-BILLING-001-invoice.md": "---\nid: TS-BILLING-001\ntitle: Invoice\ncovers: [VULN-INJ-1, FR-BILLING-001]\n---\n# Invoice\nMitigates VUL-XSS-001 and ADR-7; TS-* to come; TASK-NNNN placeholder.\n",
}
CODE = "# @" + "tests TS_AUTH_001, TS-AUTH-001\n# @" + "mitigates VUL-INJ-2\ndef login():\n    pass\n"   # split so the kit's own validator does not read these markers here


class Ids(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        install(self.home, self.project)
        (self.project / "docs/requirements/product").mkdir(parents=True, exist_ok=True)
        (self.project / "docs/requirements/product/glossary.md").write_text(GLOSSARY, encoding="utf-8")
        for rel, text in DOCS.items():
            p = self.project / "docs" / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8")
        (self.project / "src").mkdir(exist_ok=True); (self.project / "src/auth.py").write_text(CODE, encoding="utf-8")
        self.out = project_cmd(self.project, self.home, "docs", "validate", check=False).stdout

    def errors_about(self, token: str) -> list:
        return [l for l in self.out.splitlines() if l.startswith("ERROR") and l.split("`")[1:2] == [token]]   # the first quoted token is the one reported

    def test_every_invented_shape_is_reported_once_with_its_rule(self):
        want = {"TS-VUL-WEB-002": "covers: [VUL-WEB-002]", "ts-auth-002": "uppercase", "TS-AUTH-7": "exactly three digits", "TS-CATALOG-001": "not a domain code of the glossary (AUTH, BILLING)",
                "TEST-AUTH-001": "no prefix of the scheme", "VULN-INJ-1": "no prefix of the scheme", "VUL-XSS-001": "CAT is one of", "ADR-7": "four digits", "TS_AUTH_001": "never underscores", "VUL-INJ-2": "exactly three digits"}
        for token, rule in want.items():
            hits = self.errors_about(token)
            self.assertEqual(len(hits), 1, f"{token}: {hits}\n{self.out}")
            self.assertIn(rule, hits[0], hits[0])

    def test_file_name_and_uniqueness(self):
        self.assertEqual(len([l for l in self.out.splitlines() if "misnamed.md: file name does not start with its id `TS-AUTH-003`" in l]), 1, self.out)
        self.assertEqual(len([l for l in self.out.splitlines() if "id `TS-AUTH-004` is already defined" in l]), 1, self.out)

    def test_valid_ids_and_placeholders_pass(self):
        for token in ("FR-AUTH-001", "TS-AUTH-001", "VUL-WEB-002", "TS-BILLING-001", "FR-BILLING-001", "TS", "TASK-NNNN"):
            self.assertEqual(self.errors_about(token), [], token)


if __name__ == "__main__":
    unittest.main()
