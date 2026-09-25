"""Secrets the gitleaks way (secretscan.py, secretrules.py): every rule compiles, the keyword gate, entropy, the
allowlists, files that are secrets by name, the tree scan reporting a line once, the history walk over every commit
with --commits as a bound, and the [docs] tag."""
import re, subprocess, sys, unittest
from pathlib import Path

from helpers import KIT, install, project_cmd, temp_home

sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import secretscan  # noqa: E402
from secretrules import GLOBAL_ALLOW, RULES  # noqa: E402

def key(*parts: str) -> str:
    """The samples are assembled at run time from short fragments: a literal that looks like a live key stops a
    push (GitHub push protection reads test files too) and is reported by the kit's own scan of this repository."""
    return "".join(parts)


GHP = key("ghp_", "Qm4xZ7vK2pL9", "sT3nR8wY5cJ1", "hF6dG0bN4eV7", "uX2a")
STRIPE = key("sk_", "live_", "4eC39HqLyjWD", "arjtT1zdp7dc", "Xk92")
JWT = key("eyJhbGciOiJI", "UzI1NiIsInR5", "cCI6IkpXVCJ9", ".", "eyJzdWIiOiIx", "MjM0NTY3ODkw", "In0", ".", "SflKxwRJSMeK", "KF2QT4fwpMeJ", "f36POk6yJV_a", "dQssw5c")
AWS = key("AKIA", "Q7Z2M5N6", "B3C4D6EF")
GCP = key("AIzaSyD-9tSr", "ke72PouQMnMX", "-a7eZSW0jkFM", "BWY")


def ids(path: str, line: str) -> list:
    return [h[0] for h in secretscan.find(path, line)]


class Rules(unittest.TestCase):
    def test_every_rule_compiles_with_ascii_semantics(self):
        for rid, _d, rx, _k, _e, _g, allow, path in RULES:
            re.compile(rx, re.ASCII)
            for a in allow:
                for x in a.get("regexes", []) + a.get("paths", []):
                    re.compile(x, re.ASCII)
            if path:
                re.compile(path, re.ASCII)
        self.assertGreater(len(RULES), 200)
        self.assertIn("regexes", GLOBAL_ALLOW)

    def test_generated_module_carries_the_skip_marker(self):
        head = (KIT / ".aix" / "scripts" / "secretrules.py").read_text(encoding="utf-8").splitlines()[:30]
        self.assertTrue(any("aix: skip-security-scan" in l for l in head), "its own patterns look like secrets")


class Entropy(unittest.TestCase):
    def test_random_keys_score_high_and_repeats_low(self):
        self.assertGreater(secretscan.entropy("v9dn0balpqas1pcc281tn5ood1"), 3.5)
        self.assertLess(secretscan.entropy("aaaaaaaaaaaaaaaaaaaa"), 1)
        self.assertEqual(secretscan.entropy(""), 0.0)


class Find(unittest.TestCase):
    def test_provider_patterns(self):
        self.assertEqual(ids("a.py", f'token = "{GHP}"'), ["github-pat"])           # the specific rule, not the generic one too
        self.assertEqual(ids("a.js", f'const t = "{JWT}"'), ["jwt"])
        self.assertEqual(ids("a.py", f'AWS = "{AWS}"'), ["aws-access-token"])
        self.assertEqual(ids("k.py", f'key = "{GCP}"'), ["gcp-api-key"])

    def test_generic_key_needs_a_keyword_and_entropy(self):
        self.assertEqual(ids("config/env/test.js", 'zapApiKey: "v9dn0balpqas1pcc281tn5ood1",'), ["generic-api-key"])
        self.assertEqual(ids("a.py", 'api_key = "aaaaaaaaaaaaaaaaaaaa"'), [])       # entropy floor
        self.assertEqual(ids("a.py", 'value = "v9dn0balpqas1pcc281tn5ood1"'), [])   # no keyword on the line
        self.assertEqual(ids("a.py", "x = 1"), [])

    def test_allowlists(self):
        self.assertEqual(ids("a.py", 'AWS = "AKIAIOSFODNN7EXAMPLE"'), [])           # the rule's own allowlist
        self.assertEqual(ids("a.py", 'password = "${DB_PASSWORD}"'), [])            # placeholder
        self.assertEqual(ids("a.py", 'client_secret = "example_client_secret_value"'), [])   # stopword
        self.assertEqual(ids("a.py", 'api_key_length = "1234567890123"'), [])       # key_length is not a key
        self.assertEqual(ids("a.py", 'secret = "keyboard cat"'), [])                # a space is not a token

    def test_paths(self):
        self.assertEqual(ids("logo.png", 'token = "v9dn0balpqas1pcc281tn5ood1"'), [])       # never read
        self.assertTrue(secretscan.path_allowed("go.sum"))
        self.assertEqual(ids("main.tf", 'password = "Xk9v2Lm4Qp7Rt1Wz"'), ["hashicorp-tf-password"])
        self.assertEqual(ids("main.py", 'password = "Xk9v2Lm4Qp7Rt1Wz"'), ["generic-api-key"])   # the tf rule is for .tf files
        self.assertEqual(secretscan.path_secret("certs/client.p12")[0], "pkcs12-file")
        self.assertIsNone(secretscan.path_secret("a.py"))

    def test_unicode_is_not_a_word_character(self):
        self.assertEqual(ids("zh.json", '"chatbot API key": "想办法掌握聊天机器人API的内部运作情况",'), [])


def _git(cwd: Path, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "safe.directory=*", *args], cwd=cwd, check=True, capture_output=True)


class TreeAndHistory(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.p = self.home / "proj"
        (self.p / "src").mkdir(parents=True)
        install(self.home, self.p, "--agents", "claude", "--skip-all")

    def cmd(self, *args, **opts):
        return project_cmd(self.p, self.home, *args, **opts).stdout

    def test_tree_scan_reports_a_line_once_and_names_files_that_are_secrets(self):
        (self.p / "src" / "keys.py").write_text(f'GITHUB = "{GHP}"\npassword = "hunter2hunter2"\nSTRIPE = "{STRIPE}"\n', encoding="utf-8")
        (self.p / "src" / "store.p12").write_bytes(b"\x30\x82")
        out = self.cmd("code", "security", "src", check=False)
        self.assertIn("secret pattern: stripe-access-token", out)
        self.assertIn("keys.py:1  cloud / API token literal", out)
        self.assertEqual(out.count("keys.py:1 "), 1, "the register's token rule and the gitleaks rule never report one line twice")
        self.assertIn("hard-coded password / secret literal", out)
        self.assertIn("secret pattern: pkcs12-file", out)

    def test_history_walks_every_commit_unless_bounded(self):
        _git(self.p, "init", "-q"); _git(self.p, "add", "."); _git(self.p, "commit", "-qm", "kit")
        (self.p / "src" / "old.py").write_text(f'token = "{STRIPE}"\n', encoding="utf-8")
        _git(self.p, "add", "."); _git(self.p, "commit", "-qm", "leak")
        (self.p / "src" / "old.py").write_text("token = None\n", encoding="utf-8")
        _git(self.p, "add", "."); _git(self.p, "commit", "-qm", "cleaned")
        (self.p / "docs").mkdir(exist_ok=True); (self.p / "docs" / "guide.md").write_text(f"Example: `{JWT}`\n", encoding="utf-8")
        _git(self.p, "add", "."); _git(self.p, "commit", "-qm", "docs")
        out = self.cmd("code", "vulnerabilities", "--history")
        self.assertIn("secret pattern: stripe-access-token in history", out)
        self.assertNotIn(".aix/", out, "the kit's own files are never secrets")
        self.assertIn("every commit", out)
        self.assertRegex(out, r"docs/guide\.md .*\[docs\]")
        gate = project_cmd(self.p, self.home, "code", "vulnerabilities", "--history", "--gate", check=False)
        self.assertIn("GATE FAILED", gate.stderr, "a token in an old commit is a leak until rotated")
        bounded = project_cmd(self.p, self.home, "code", "vulnerabilities", "--history", "--commits", "1", "--gate", check=False)
        self.assertNotIn("stripe-access-token", bounded.stdout)
        self.assertIn("last 1 commits", bounded.stdout)
        self.assertIn("GATE PASSED", bounded.stdout, "the docs example alone is listed, not gated")


if __name__ == "__main__":
    unittest.main()
