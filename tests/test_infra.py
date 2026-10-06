"""Infrastructure and framework rules (infrarules.py), the categories semgrep adds: GitHub Actions (mutable tags,
untrusted context in run, curl piped to a shell), dependabot cooldown, .npmrc release age, sudo in a Dockerfile,
Kubernetes containers, compose services, express session cookies and secrets, external assets without integrity,
Spring actuator and request mappings, postMessage to any origin; the negatives stay quiet; the root's own files
are scanned whatever the code roots."""
import sys, unittest
from pathlib import Path

from helpers import KIT, install, project_cmd, temp_home

sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import infrarules  # noqa: E402

WORKFLOW = """name: ci
on: [pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@b39b52d1213e96004bfcb1c61a8a6fa8ab84f3e8 # v4.0.1
      - uses: ./.github/actions/local
      - name: Title
        run: echo "${{ github.event.pull_request.title }}"
      - name: Safe
        env:
          TITLE: ${{ github.event.pull_request.title }}
        run: echo "$TITLE" && echo ${{ github.repository }}
      - name: Install
        run: |
          curl -sL https://example.com/install.sh | bash
      - name: Own outputs
        run: echo ${{ steps.meta.outputs.version }} ${{ needs.build.outputs.name }}
"""
K8S = """apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - image: postgres:16
          name: db
          env:
            - name: POSTGRES_USER
              value: app
        - image: nginx:1.25
          name: web
          securityContext:
            runAsNonRoot: true
            allowPrivilegeEscalation: false
"""
K8S_HARDENED = """apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - image: dsyer/petclinic
          name: app
          securityContext:
            runAsNonRoot: true
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
            seccompProfile:
              type: RuntimeDefault
        - name: cache
          securityContext: {runAsNonRoot: true, allowPrivilegeEscalation: false, readOnlyRootFilesystem: true, capabilities: {drop: [ALL]}, seccompProfile: {type: RuntimeDefault}}
          image: redis:latest
"""
COMPOSE = """services:
  web:
    build: .
  db:
    image: postgres:16
  cache:
    image: redis:7
    read_only: true
    security_opt:
      - no-new-privileges:true
"""
EXPRESS = """const session = require('express-session');
app.use(session({
  secret: 'keyboard cat',
  resave: false,
}));
app.use(session({
  secret: process.env.SECRET,
  name: 'sid',
  cookie: { httpOnly: true, secure: true, domain: 'x.io', path: '/', maxAge: 3600 },
}));
window.parent.postMessage(payload, '*');
window.parent.postMessage(payload, 'https://x.io');
"""
HTML = """<link rel="stylesheet"
      href="https://cdn.example.com/a.css">
<script src="https://cdn.example.com/b.js" integrity="sha384-abc" crossorigin="anonymous"></script>
<script src="/static/own.js"></script>
"""
JAVA = """@RequestMapping("/owners")
@RestController
@Hints({
  "one",
  "two"})
public class OwnerController {
  @RequestMapping("/all")
  public String all() { return ""; }
  @RequestMapping(value = "/one", method = RequestMethod.GET)
  public String one() { return ""; }
  @GetMapping("/two")
  public String two() { return ""; }
}
"""


def titles(f: Path) -> list:
    return sorted(fx[2] for fx in infrarules.findings(f))


class Rules(unittest.TestCase):
    def setUp(self):
        self.root = temp_home(self)

    def write(self, name: str, text: str) -> Path:
        f = self.root / name; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(text, encoding="utf-8"); return f

    def test_workflow(self):
        found = infrarules.findings(self.write(".github/workflows/ci.yml", WORKFLOW))
        self.assertEqual([(fx[2], fx[4]) for fx in found], [("workflow without a permissions block (the token keeps the repository default)", 1), ("action pinned to a mutable tag", 7), ("workflow shell injection: untrusted context in run", 11), ("remote script piped to a shell", 17)])
        quiet = self.write(".github/workflows/ok.yml", "name: ok\non: [push]\npermissions:\n  contents: read\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: make\n")
        self.assertEqual(titles(quiet), [], "a top-level permissions block")
        per_job = self.write(".github/workflows/jobs.yml", "name: pj\non: [push]\njobs:\n  build:\n    permissions:\n      contents: read\n    runs-on: ubuntu-latest\n    steps:\n      - run: make\n  test:\n    permissions: write-all\n    runs-on: ubuntu-latest\n    steps:\n      - run: make\n")
        self.assertEqual([(fx[2], fx[4]) for fx in infrarules.findings(per_job)], [("workflow token permissions set to write-all", 11)])

    def test_dependabot_and_npmrc(self):
        self.assertEqual(titles(self.write(".github/dependabot.yml", "version: 2\nupdates:\n  - package-ecosystem: npm\n    directory: /\n  - package-ecosystem: pip\n    cooldown:\n      default-days: 7\n")), ["dependabot update without a cooldown"])
        self.assertEqual(titles(self.write(".npmrc", "package-lock=false\n")), [".npmrc without a minimum release age"])
        self.assertEqual(titles(self.write("sub/.npmrc", "min-release-age=7\n")), [])

    def test_containers(self):
        self.assertEqual(titles(self.write("Dockerfile", "FROM x\nRUN echo 'root:pw' | chpasswd\nRUN sudo apt-get install -y curl\nUSER app\n")), ["password set in the image (chpasswd / passwd)", "sudo in a Dockerfile"])
        found = infrarules.findings(self.write("k8s/db.yml", K8S))
        self.assertEqual([(fx[2], fx[4]) for fx in found], [("container may run as root", 7), ("container allows privilege escalation", 7), ("container with a writable root filesystem", 7), ("container keeps its Linux capabilities", 7), ("container without a seccomp profile", 7),
                                                            ("container with a writable root filesystem", 12), ("container keeps its Linux capabilities", 12), ("container without a seccomp profile", 12)])
        hardened = self.write("k8s/web.yml", K8S_HARDENED)
        self.assertEqual([(fx[2], fx[4]) for fx in infrarules.findings(hardened)], [("image without a pinned tag", 7), ("image without a pinned tag", 19)], "untagged and latest images; the hardened containers are silent")
        self.assertEqual(titles(self.write("k8s/config.yml", "apiVersion: v1\nkind: ConfigMap\ndata:\n  a: b\n")), [])
        found = infrarules.findings(self.write("docker-compose.yml", COMPOSE))
        self.assertEqual([(fx[2], fx[4]) for fx in found], [("compose service without no-new-privileges", 4), ("compose service with a writable root filesystem", 4)])

    def test_express_and_post_message(self):
        found = infrarules.findings(self.write("app.js", EXPRESS))
        self.assertEqual([(fx[2], fx[4]) for fx in found], [("session cookie without httpOnly, secure, domain, path, expires or maxAge, name", 2), ("session secret hard-coded", 3), ("postMessage to any origin", 11)])

    def test_pages_and_spring(self):
        found = infrarules.findings(self.write("templates/base.html", HTML))
        self.assertEqual([(fx[2], fx[4]) for fx in found], [("external script or stylesheet without integrity", 1)], "a tag spanning two lines, anchored on its first")
        found = infrarules.findings(self.write("src/OwnerController.java", JAVA))
        self.assertEqual([(fx[2], fx[4]) for fx in found], [("@RequestMapping without a method: every verb, CSRF-exposed", 7)], "class-level mappings (past multi-line annotations) and ones with a method are not findings")
        self.assertEqual(titles(self.write("src/main/resources/application.properties", "management.endpoints.web.exposure.include=*\n")), ["every actuator endpoint exposed"])
        self.assertEqual(titles(self.write("src/main/resources/application.yml", "management:\n  endpoints:\n    web:\n      exposure:\n        include: \"*\"\n")), ["every actuator endpoint exposed"])


class RootFiles(unittest.TestCase):
    def test_root_files_are_scanned_whatever_the_code_roots(self):
        home = temp_home(self); p = home / "proj"; (p / "src").mkdir(parents=True); (p / ".github" / "workflows").mkdir(parents=True)
        (p / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
        (p / ".github" / "workflows" / "ci.yml").write_text(WORKFLOW, encoding="utf-8")
        (p / "docker-compose.yml").write_text(COMPOSE, encoding="utf-8")
        (p / "k8s").mkdir(); (p / "k8s" / "db.yml").write_text(K8S, encoding="utf-8")
        install(home, p, "--agents", "claude", "--skip-all")
        out = project_cmd(p, home, "code", "security", "src", check=False).stdout
        self.assertIn("action pinned to a mutable tag", out); self.assertIn("compose service without no-new-privileges", out)
        self.assertIn("k8s/db.yml:7", out, "a manifest folder outside the code roots is still scanned")
        self.assertEqual(out.count("ci.yml:7 "), 1, "once, even when the root is also a path")


if __name__ == "__main__":
    unittest.main()
