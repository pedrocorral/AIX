"""26. `aix code licenses`: every ecosystem read from metadata on disk (Python dist-info, npm node_modules, the Cargo
registry cache, the Maven repository), classes and expressions, what a manifest declares but nothing installs, the
decisions in .aix/config.yaml (`allow`, `known`), the gate and the report."""
import unittest
from helpers import install, project_cmd, temp_home


def write(root, files: dict):
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")


class Licenses(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        site = ".venv/lib/python3.13/site-packages"
        write(self.project, {
            f"{site}/requests-2.32.3.dist-info/METADATA": "Name: requests\nVersion: 2.32.3\nLicense: Apache-2.0\n",
            f"{site}/gpl_thing-1.0.dist-info/METADATA": "Name: gpl-thing\nVersion: 1.0\nClassifier: License :: OSI Approved :: GNU General Public License v3 (GPLv3)\n",
            f"{site}/mystery-0.1.dist-info/METADATA": "Name: mystery\nVersion: 0.1\nLicense: UNKNOWN\n",
            f"{site}/expr-3.0.dist-info/METADATA": "Name: expr\nVersion: 3.0\nLicense-Expression: MIT OR GPL-2.0-only\n",
            "requirements.txt": "requests==2.32.3\ngpl-thing\nnot-installed-lib>=1\n",
            "node_modules/isc-lib/package.json": '{"name": "isc-lib", "version": "1.2.3", "license": "ISC"}\n',
            "node_modules/@scope/mpl-lib/package.json": '{"name": "@scope/mpl-lib", "version": "0.4.0", "license": "MPL-2.0"}\n',
            "node_modules/nolicense/package.json": '{"name": "nolicense", "version": "9.9.9"}\n',
            "node_modules/private-thing/package.json": '{"name": "private-thing", "version": "1.0.0", "license": "UNLICENSED"}\n',
            "node_modules/both/package.json": '{"name": "both", "version": "1.0.0", "license": "MIT AND GPL-3.0"}\n',
            "package.json": '{"dependencies": {"isc-lib": "^1", "ghost": "^2"}}\n',
            "Cargo.lock": '[[package]]\nname = "serde"\nversion = "1.0.200"\n\n[[package]]\nname = "absent"\nversion = "0.1.0"\n',
            "pom.xml": "<project><dependencies><dependency><groupId>org.apache.commons</groupId><artifactId>commons-lang3</artifactId><version>3.17.0</version></dependency></dependencies></project>\n",
            "src/app.py": "x = 1\n",
        })
        write(self.home, {
            "cargo/registry/src/index/serde-1.0.200/Cargo.toml": '[package]\nname = "serde"\nlicense = "MIT OR Apache-2.0"\n',
            ".m2/repository/org/apache/commons/commons-lang3/3.17.0/commons-lang3-3.17.0.pom": "<project><licenses><license><name>Apache-2.0</name></license></licenses></project>\n",
        })
        install(self.home, self.project)
        self.env = {"CARGO_HOME": str(self.home / "cargo")}

    def report(self, *args, check=True):
        return project_cmd(self.project, self.home, "code", "licenses", *args, check=check, extra_env=self.env)

    def test_every_ecosystem_and_class(self):
        out = self.report().stdout
        self.assertIn("installed packages 11 (cargo 1, maven 1, npm 5, python 4)", out)
        self.assertIn("permissive 5   weak copyleft 1   strong copyleft 2   proprietary 1   unknown 2", out)
        self.assertRegex(out, r"STRONG   gpl-thing 1.0  GNU General Public License v3 \(GPLv3\)  \(python\)")
        self.assertRegex(out, r"STRONG   both 1.0.0  MIT AND GPL-3.0  \(npm\)")
        self.assertRegex(out, r"WEAK     @scope/mpl-lib 0.4.0  MPL-2.0  \(npm\)")
        self.assertRegex(out, r"PROPRIETARY private-thing 1.0.0  UNLICENSED")
        self.assertRegex(out, r"UNKNOWN  mystery 0.1  \(none\)", "License: UNKNOWN says nothing")
        self.assertRegex(out, r"UNKNOWN  nolicense 9.9.9  \(none\)")
        self.assertNotIn("expr 3.0", out, "MIT OR GPL takes the permissive side: not listed")
        self.assertNotIn("serde", out); self.assertNotIn("commons-lang3", out)
        self.assertIn("declared but not installed: 2", out)
        self.assertIn("NOT INSTALLED  ghost", out); self.assertIn("NOT INSTALLED  not-installed-lib", out)

    def test_gate_and_decisions(self):
        r = self.report("--gate", check=False)
        self.assertEqual(r.returncode, 1); self.assertIn("GATE FAILED: 5 licence(s) to decide", r.stderr)
        cfg = self.project / ".aix" / "config.yaml"
        cfg.write_text(cfg.read_text(encoding="utf-8") + "licenses_allow: [GPL-3.0, UNLICENSED]   # ADR-0007\nlicenses_known:\n  mystery: MIT\n  nolicense: BSD-3-Clause\n", encoding="utf-8")
        out = self.report().stdout
        self.assertIn("strong copyleft 1   proprietary 0   unknown 0", out, "GPLv3 by classifier is not the id GPL-3.0; the rest is decided\n" + out)
        cfg.write_text(cfg.read_text(encoding="utf-8").replace("licenses_allow: [GPL-3.0, UNLICENSED]", "licenses_allow: [GPL-3.0, UNLICENSED, GNU General Public License v3 (GPLv3)]"), encoding="utf-8")
        r = self.report("--gate", check=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertIn("GATE PASSED", r.stdout)

    def test_report_file_and_policy_step(self):
        self.report("--report")
        self.assertTrue((self.project / "docs" / "tests" / "code-licenses.md").exists())
        out = project_cmd(self.project, self.home, "policy", "show", "release").stdout
        self.assertIn("licenses", out)


if __name__ == "__main__":
    unittest.main()
