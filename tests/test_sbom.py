"""The bill of materials (sbom.py, cvss.py): the CVSS arithmetic on published scores, purls, the CycloneDX and SPDX
shapes, severities from a vector or a database label, licences read from disk, and the composition gate with its
threshold, all offline through fakes for OSV and deps.dev."""
import json, sys, unittest

from helpers import KIT, install, project_cmd, temp_home

sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import cvecheck, cvss, sbom  # noqa: E402

LOCK = {"name": "app", "lockfileVersion": 3, "packages": {"": {"name": "app"}, "node_modules/lodash": {"version": "4.17.20"}, "node_modules/@scope/left": {"version": "1.0.0"}}}
VULNS = {
    "GHSA-p6mc-m468-83gw": {"id": "GHSA-p6mc-m468-83gw", "summary": "Prototype pollution in lodash", "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:H"}],
                            "affected": [{"package": {"name": "lodash", "ecosystem": "npm"}, "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "4.17.21"}]}]}]},
    "GHSA-low": {"id": "GHSA-low", "summary": "A minor one", "database_specific": {"severity": "LOW"}, "affected": [{"package": {"name": "lodash", "ecosystem": "npm"}}]},
}


class Cvss(unittest.TestCase):
    def test_published_scores(self):
        for vector, want in [("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H", 10.0), ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", 9.8),
                             ("CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N", 6.1), ("CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N", 5.5),
                             ("CVSS:3.0/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:H", 5.9), ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N", 0.0)]:
            self.assertEqual(cvss.base_score(vector), want, vector)
        self.assertIsNone(cvss.base_score("CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"))
        self.assertIsNone(cvss.base_score("not a vector"))

    def test_labels_and_rank(self):
        self.assertEqual([cvss.label(x) for x in (10.0, 7.0, 6.9, 0.1, 0.0, None)], ["critical", "high", "medium", "low", "none", "unknown"])
        self.assertLess(cvss.rank("critical"), cvss.rank("high")); self.assertGreater(cvss.rank("unknown"), cvss.rank("low"))


class Purl(unittest.TestCase):
    def test_shapes(self):
        self.assertEqual(sbom.purl("Maven", "org.apache.commons:commons-lang3", "3.14.0"), "pkg:maven/org.apache.commons/commons-lang3@3.14.0")
        self.assertEqual(sbom.purl("npm", "@scope/left", "1.0.0"), "pkg:npm/%40scope/left@1.0.0")
        self.assertEqual(sbom.purl("crates.io", "regex", "1.10.0"), "pkg:cargo/regex@1.10.0")
        self.assertEqual(sbom.purl("Go", "github.com/gin-gonic/gin", "1.8.1"), "pkg:golang/github.com/gin-gonic/gin@1.8.1")


class Severity(unittest.TestCase):
    def test_vector_then_label_then_unknown(self):
        self.assertEqual(cvecheck.severity(VULNS["GHSA-p6mc-m468-83gw"]), ("high", 8.6))
        self.assertEqual(cvecheck.severity(VULNS["GHSA-low"]), ("low", None))
        self.assertEqual(cvecheck.severity({"database_specific": {"severity": "MODERATE"}}), ("medium", None))
        self.assertEqual(cvecheck.severity({}), ("unknown", None))
        self.assertEqual(cvecheck.fixed_version(VULNS["GHSA-p6mc-m468-83gw"], "lodash"), "4.17.21")
        two = {"affected": [{"package": {"name": "tomcat"}, "ranges": [{"events": [{"introduced": "9.0"}, {"fixed": "9.0.121"}, {"introduced": "11.0"}, {"fixed": "11.0.23"}]}]}]}
        self.assertEqual(cvecheck.fixed_version(two, "tomcat", "11.0.22"), "11.0.23", "the fix on the current branch, not the lowest fix of the advisory")
        self.assertEqual(cvecheck.fixed_version(two, "tomcat", "12.0.0"), "11.0.23", "nothing above: the highest listed")


class Bill(unittest.TestCase):
    """A project with a package-lock.json and one installed Python package; OSV and deps.dev are fakes."""
    def setUp(self):
        self.home = temp_home(self); self.p = self.home / "app"; self.p.mkdir()
        (self.p / "package-lock.json").write_text(json.dumps(LOCK), encoding="utf-8")
        info = self.p / ".venv" / "lib" / "python3.12" / "site-packages" / "gpl_thing-1.0.dist-info"; info.mkdir(parents=True)
        (info / "METADATA").write_text("Name: gpl-thing\nVersion: 1.0\nLicense: GPL-3.0-only\n", encoding="utf-8")
        cvecheck.POST = lambda body: [{"vulns": [{"id": "GHSA-p6mc-m468-83gw"}, {"id": "GHSA-low"}]} if q["package"]["name"] == "lodash" else {} for q in json.loads(body)["queries"]]
        cvecheck.FETCH_VULN = lambda vid: VULNS.get(vid)
        cvecheck.OSV_CACHE = self.home / "osv"
        self.addCleanup(setattr, cvecheck, "POST", cvecheck._post); self.addCleanup(setattr, cvecheck, "FETCH_VULN", cvecheck._fetch_vuln)

    def test_bill_cyclonedx_and_spdx(self):
        bill = sbom.build(self.p)
        self.assertEqual({c["purl"] for c in bill["components"]}, {"pkg:npm/lodash@4.17.20", "pkg:npm/%40scope/left@1.0.0"})
        self.assertEqual(sorted(a["severity"] for a in bill["advisories"]), ["high", "low"])
        cdx = sbom.cyclonedx(bill)
        self.assertEqual((cdx["bomFormat"], cdx["specVersion"], len(cdx["components"]), len(cdx["vulnerabilities"])), ("CycloneDX", "1.5", 2, 2))
        v = next(x for x in cdx["vulnerabilities"] if x["id"] == "GHSA-p6mc-m468-83gw")
        self.assertEqual((v["ratings"][0]["severity"], v["ratings"][0]["score"], v["affects"][0]["ref"], v["recommendation"]), ("high", 8.6, "pkg:npm/lodash@4.17.20", "upgrade to 4.17.21"))
        spdx = sbom.spdx(bill)
        self.assertEqual((spdx["spdxVersion"], len(spdx["packages"]), len(spdx["relationships"])), ("SPDX-2.3", 2, 2))
        self.assertEqual(spdx["packages"][0]["externalRefs"][0]["referenceType"], "purl")

    def test_verdict_follows_the_threshold(self):
        bill = sbom.build(self.p)
        self.assertTrue(bill["licences_read"], "a dist-info was on disk")
        over, bad = sbom.verdict(bill, "high")
        self.assertEqual([a["id"] for a in over], ["GHSA-p6mc-m468-83gw"])
        self.assertEqual(bad, [], "the npm packages are not installed on disk (no licence read) and the GPL one is not in the bill")
        self.assertEqual({c["licence"] for c in bill["components"]}, {("", "")})
        self.assertEqual(len(sbom.verdict(bill, "low")[0]), 2)
        self.assertEqual(len(sbom.verdict(bill, "critical")[0]), 0)


class Command(unittest.TestCase):
    def test_writes_the_file_and_gates(self):
        home = temp_home(self); p = home / "app"; p.mkdir()
        (p / "package-lock.json").write_text(json.dumps({"name": "app", "lockfileVersion": 3, "packages": {"": {}}}), encoding="utf-8")
        install(home, p, "--agents", "claude", "--skip-all")
        r = project_cmd(p, home, "code", "sbom", check=False)
        self.assertIn("Software bill of materials", r.stdout)
        self.assertTrue((p / "docs" / "security" / "sbom.cdx.json").exists())
        self.assertEqual(json.loads((p / "docs" / "security" / "sbom.cdx.json").read_text())["bomFormat"], "CycloneDX")
        r = project_cmd(p, home, "blackduck", check=False)
        self.assertIn("POLICY", r.stdout)
        self.assertRegex(r.stdout + r.stderr, r"GATE (PASSED|FAILED)")
        self.assertIn("Black Duck", project_cmd(p, home, "help", "blackduck").stdout)


if __name__ == "__main__":
    unittest.main()
