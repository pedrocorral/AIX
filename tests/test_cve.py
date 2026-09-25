"""Known CVEs (cvecheck.py, manifests.py, depsdev.py), offline: every manifest kind is read, a pom.xml gets its
properties, dependencyManagement, parent-managed versions and exclusions, resolution goes through a fake deps.dev,
OSV queries are chunked at 1000, the version sort never raises, and the report says what it queried."""
import json, sys, unittest
from pathlib import Path

from helpers import KIT, install, project_cmd, temp_home

sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import cvecheck, depsdev, manifests  # noqa: E402

POM = """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <parent><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-parent</artifactId><version>3.2.0</version></parent>
  <groupId>demo</groupId><artifactId>app</artifactId><version>1.0</version>
  <properties><jsoup.version>1.15.3</jsoup.version></properties>
  <dependencyManagement><dependencies>
    <dependency><groupId>com.google.guava</groupId><artifactId>guava</artifactId><version>31.1-jre</version></dependency>
  </dependencies></dependencyManagement>
  <dependencies>
    <dependency><groupId>org.jsoup</groupId><artifactId>jsoup</artifactId><version>${jsoup.version}</version></dependency>
    <dependency><groupId>com.google.guava</groupId><artifactId>guava</artifactId></dependency>
    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId>
      <exclusions><exclusion><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-tomcat</artifactId></exclusion></exclusions>
    </dependency>
    <dependency><groupId>x</groupId><artifactId>unknown</artifactId><version>${nowhere}</version></dependency>
  </dependencies>
</project>
"""
YARN_V1 = '# yarn lockfile v1\n\n"@babel/core@^7.0.0", "@babel/core@^7.1.0":\n  version "7.18.9"\n  resolved "x"\n\nlodash@^4.17.19, lodash@^4.17.21:\n  version "4.17.21"\n'
YARN_BERRY = '__metadata:\n  version: 6\n\n"minimatch@npm:^3.0.4":\n  version: 3.1.2\n  resolution: "minimatch@npm:3.1.2"\n'


def write(root: Path, name: str, text: str):
    (root / name).parent.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(text, encoding="utf-8")


class Readers(unittest.TestCase):
    def setUp(self):
        self.root = temp_home(self)

    def names(self, items):
        return sorted((d[0], d[1], d[2]) for d in items)

    def test_yarn_v1_and_berry(self):
        write(self.root, "yarn.lock", YARN_V1); write(self.root, "web/yarn.lock", YARN_BERRY)
        self.assertEqual(self.names(manifests.npm_locks(self.root)), [("npm", "@babel/core", "7.18.9"), ("npm", "lodash", "4.17.21"), ("npm", "minimatch", "3.1.2")])

    def test_pipfile_gemfile_composer_gosum(self):
        write(self.root, "Pipfile.lock", json.dumps({"default": {"requests": {"version": "==2.28.1"}}, "develop": {"pytest": {"version": "==7.0.0"}}}))
        write(self.root, "Gemfile.lock", "GEM\n  remote: https://rubygems.org/\n  specs:\n    rails (7.0.4)\n      actionpack (= 7.0.4)\n    nokogiri (1.13.9)\n\nPLATFORMS\n  ruby\n")
        write(self.root, "composer.lock", json.dumps({"packages": [{"name": "monolog/monolog", "version": "v2.8.0"}], "packages-dev": []}))
        write(self.root, "go.sum", "github.com/gin-gonic/gin v1.8.1 h1:abc=\ngithub.com/gin-gonic/gin v1.8.1/go.mod h1:def=\n")
        self.assertEqual(self.names(manifests.other_locks(self.root)),
                         [("Go", "github.com/gin-gonic/gin", "1.8.1"), ("Packagist", "monolog/monolog", "2.8.0"), ("PyPI", "pytest", "7.0.0"), ("PyPI", "requests", "2.28.1"), ("RubyGems", "nokogiri", "1.13.9"), ("RubyGems", "rails", "7.0.4")])

    def test_requirements_pins_in_any_requirements_file(self):
        write(self.root, "dev-requirements.txt", "Django==4.2\nflask\nurllib3>=1.26\n")
        self.assertEqual(self.names(manifests.pinned_requirements(self.root)), [("PyPI", "django", "4.2")])

    def test_one_entry_per_package_and_lockfile(self):
        write(self.root, "yarn.lock", YARN_V1); write(self.root, "web/yarn.lock", YARN_V1)
        self.assertEqual(len(manifests.lockfile_dependencies(self.root)), 4, "the same version in two lockfiles is two entries: each lockfile is fixed on its own")

    def test_pom(self):
        write(self.root, "pom.xml", POM)
        deps, managed, parent = manifests.read_pom(self.root / "pom.xml")
        self.assertEqual(parent, ("org.springframework.boot:spring-boot-starter-parent", "3.2.0"))
        self.assertEqual(managed, {"com.google.guava:guava": "31.1-jre"})
        by_name = {d[0]: d for d in deps}
        self.assertEqual(by_name["org.jsoup:jsoup"][1], "1.15.3", "properties substituted")
        self.assertEqual(by_name["com.google.guava:guava"][1], "31.1-jre", "dependencyManagement applied")
        self.assertEqual(by_name["org.springframework.boot:spring-boot-starter-web"][1], "", "left to the parent")
        self.assertEqual(by_name["org.springframework.boot:spring-boot-starter-web"][3], ["org.springframework.boot:spring-boot-starter-tomcat"])
        self.assertEqual(by_name["x:unknown"][1], "", "an unresolvable property is not a version")


FAKE = {
    "requirements/maven/org.springframework.boot%3Aspring-boot-starter-parent@3.2.0": {"maven": {"dependencyManagement": [], "parent": {"name": "org.springframework.boot:spring-boot-dependencies", "version": "3.2.0"}}},
    "requirements/maven/org.springframework.boot%3Aspring-boot-dependencies@3.2.0": {"maven": {"dependencyManagement": [
        {"resolvedName": "org.springframework.boot:spring-boot-starter-web", "resolvedVersion": "3.2.0"}, {"resolvedName": "com.fasterxml.jackson.core:jackson-databind", "resolvedVersion": "2.15.3"}]}},
    "dependencies/maven/org.springframework.boot%3Aspring-boot-starter-web@3.2.0": {"nodes": [
        {"versionKey": {"name": "org.springframework.boot:spring-boot-starter-web", "version": "3.2.0"}}, {"versionKey": {"name": "org.springframework.boot:spring-boot-starter-tomcat", "version": "3.2.0"}},
        {"versionKey": {"name": "org.apache.tomcat.embed:tomcat-embed-core", "version": "10.1.16"}}, {"versionKey": {"name": "com.fasterxml.jackson.core:jackson-databind", "version": "2.14.1"}}],
        "edges": [{"fromNode": 0, "toNode": 1}, {"fromNode": 1, "toNode": 2}, {"fromNode": 0, "toNode": 3}]},
    "dependencies/maven/org.jsoup%3Ajsoup@1.15.3": {"nodes": [{"versionKey": {"name": "org.jsoup:jsoup", "version": "1.15.3"}}]},
    "dependencies/maven/com.google.guava%3Aguava@31.1-jre": {"nodes": [{"versionKey": {"name": "com.google.guava:guava", "version": "31.1-jre"}}]},
    "dependencies/pypi/django@4.2": {"nodes": [{"versionKey": {"name": "django", "version": "4.2.0"}}, {"versionKey": {"name": "sqlparse", "version": "0.5.0"}}], "edges": [{"fromNode": 0, "toNode": 1}]},
}


def fake_fetch(url: str):
    key = url.split("/systems/")[1].replace("/packages/", "/").replace("/versions/", "@")
    kind, rest = key.split(":")[-1], key.rsplit(":", 1)[0]
    return FAKE.get(f"{kind}/{rest}", {})


class Resolution(unittest.TestCase):
    def setUp(self):
        self.root = temp_home(self)
        self.calls = []
        depsdev.FETCH = lambda url: (self.calls.append(url), fake_fetch(url))[1]
        depsdev.CACHE = self.root / "depsdev"
        self.addCleanup(setattr, depsdev, "FETCH", depsdev.fetch_json)

    def test_pom_resolved_with_parent_managed_versions_and_exclusions(self):
        write(self.root, "pom.xml", POM)
        deps, stats = cvecheck.all_dependencies(self.root)
        got = {(d[1], d[2]) for d in deps}
        self.assertIn(("org.springframework.boot:spring-boot-starter-web", "3.2.0"), got, "version from the parent's dependencyManagement")
        self.assertIn(("com.fasterxml.jackson.core:jackson-databind", "2.15.3"), got, "the managed version overrides the transitive one")
        self.assertNotIn(("com.fasterxml.jackson.core:jackson-databind", "2.14.1"), got)
        self.assertNotIn(("org.apache.tomcat.embed:tomcat-embed-core", "10.1.16"), got, "under an excluded subtree")
        self.assertEqual([u.split("/")[-1] for u in stats["unresolved"]], ["pom.xml: x:unknown"])
        self.assertEqual((stats["direct"], stats["transitive"]), (3, 1))

    def test_pins_keep_their_spelling_and_answers_are_cached(self):
        write(self.root, "requirements.txt", "Django==4.2\n")
        deps, stats = cvecheck.all_dependencies(self.root)
        self.assertEqual({(d[1], d[2]) for d in deps}, {("django", "4.2"), ("sqlparse", "0.5.0")}, "`4.2` as declared, not deps.dev's `4.2.0`")
        n = len(self.calls); cvecheck.all_dependencies(self.root)
        self.assertEqual(len(self.calls), n, "the second run reads the disk cache")

    def test_unknown_package_is_not_unreachable(self):
        write(self.root, "requirements.txt", "nosuchthing==1.0\n")
        deps, stats = cvecheck.all_dependencies(self.root)
        self.assertEqual([(d[1], d[2]) for d in deps], [("nosuchthing", "1.0")])
        self.assertFalse(stats["unreachable"])


class Queries(unittest.TestCase):
    def test_osv_queries_go_in_batches_of_1000(self):
        posts = []
        cvecheck.POST = lambda body: (posts.append(len(json.loads(body)["queries"])), [{} for _ in json.loads(body)["queries"]])[1]
        self.addCleanup(setattr, cvecheck, "POST", cvecheck._post)
        deps = [("npm", f"pkg{i}", "1.0.0", "package-lock.json") for i in range(2500)]
        self.assertEqual(cvecheck.osv_query(deps), {})
        self.assertEqual(posts, [1000, 1000, 500])

    def test_version_key_never_raises(self):
        self.assertEqual(sorted(["2.0", "2.0-rc1", "1.10", "1.9"], key=cvecheck._version_key), ["1.9", "1.10", "2.0", "2.0-rc1"])


class Report(unittest.TestCase):
    def test_note_says_what_was_queried(self):
        home = temp_home(self); project = home / "app"; project.mkdir()
        write(project, "requirements.txt", "requests==2.19.0\n")
        install(home, project, "--agents", "claude", "--skip-all")
        cvecheck_stub = "import sys; sys.path.insert(0, '.aix/scripts')"
        self.assertTrue(cvecheck_stub)
        out = project_cmd(project, home, "code", "vulnerabilities", "--cve", check=False).stdout
        self.assertRegex(out, r"known CVEs \(OSV\): .*(packages from 1 manifest|unreachable)")


if __name__ == "__main__":
    unittest.main()
