"""16. Policies: anarchy and its synonyms, list/show/use/off, aix check verdicts, task done refused and --force,
a task's own policy, a layer's defaults.yaml, a custom policy with its own check, the ## Cycle section in AGENTS.md."""
import re, unittest
from helpers import KIT, assert_healthy, config, fixture, install, make_fork, project_cmd, temp_home, upgrade

ACME = KIT / "examples" / "acme"


def agents_md(project):
    return (project / "AGENTS.md").read_text(encoding="utf-8")


class Anarchy(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        install(self.home, self.project)

    def test_default_is_anarchy_and_nothing_is_checked(self):
        out = project_cmd(self.project, self.home, "policy").stdout
        self.assertRegex(out, r"(?m)^\* anarchy")
        self.assertIn("(kit)", out)
        r = project_cmd(self.project, self.home, "check")
        self.assertIn("policy: anarchy", r.stdout)
        self.assertIn("Nothing is checked", r.stdout)
        self.assertNotIn("## Cycle", agents_md(self.project))
        project_cmd(self.project, self.home, "task", "new", "Anything")
        project_cmd(self.project, self.home, "task", "start", "TASK-0002")
        r = project_cmd(self.project, self.home, "task", "done", "TASK-0002")
        self.assertIn("completed", r.stdout)

    def test_synonyms(self):
        for word in ("none", "nothing", "freedom", "anarchy"):
            project_cmd(self.project, self.home, "policy", "use", "standard")
            r = project_cmd(self.project, self.home, "policy", "use", word)
            self.assertIn("policy: anarchy", r.stdout, word)
            self.assertRegex(config(self.project), r"(?m)^policy: anarchy")
            self.assertNotIn("## Cycle", agents_md(self.project))
        self.assertIn("also: none, nothing, freedom", project_cmd(self.project, self.home, "policy", "show", "freedom").stdout)


class Policies(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = fixture("flat-project", self.home / "flat")
        install(self.home, self.project)
        project_cmd(self.project, self.home, "code", "find", "--yes")

    def test_list_show_use_off(self):
        out = project_cmd(self.project, self.home, "policy", "list").stdout
        for name in ("minimal", "standard", "hotfix", "release"):
            self.assertIn(name, out)
        show = project_cmd(self.project, self.home, "policy", "show", "standard").stdout
        self.assertRegex(show, r"style\s+required\s+check\s+aix code style --gate")
        self.assertRegex(show, r"spec\s+advised\s+skill\s+spec-write-requirement")
        r = project_cmd(self.project, self.home, "policy", "use", "minimal")
        self.assertRegex(config(self.project), r"(?m)^policy: minimal")
        self.assertRegex(project_cmd(self.project, self.home, "policy").stdout, r"(?m)^\* minimal")
        cycle = agents_md(self.project)
        self.assertIn("## Cycle", cycle)
        self.assertIn("Policy `minimal` (config)", cycle)
        self.assertIn("- style (required): `aix code style --gate`", cycle)
        project_cmd(self.project, self.home, "policy", "off")
        self.assertNotIn("## Cycle", agents_md(self.project))
        r = project_cmd(self.project, self.home, "policy", "use", "nope", check=False)
        self.assertNotEqual(r.returncode, 0)
        assert_healthy(self, self.project, self.home)

    def test_check_passes_and_a_required_failure_blocks_task_done(self):
        project_cmd(self.project, self.home, "policy", "use", "minimal")
        r = project_cmd(self.project, self.home, "check")
        self.assertRegex(r.stdout, r"style\s+required\s+pass")
        self.assertRegex(r.stdout, r"docs\s+required\s+pass")
        self.assertIn("cycle complete", r.stdout)
        project_cmd(self.project, self.home, "task", "new", "Break the style")
        project_cmd(self.project, self.home, "task", "start", "TASK-0002")
        big = self.project / "mytool" / "big.py"
        big.write_text("def huge(a, b, c, d, e, f, g):\n" + "".join(f"    x{i} = {i}\n" for i in range(70)) + "    return a\n", encoding="utf-8")
        r = project_cmd(self.project, self.home, "check", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertRegex(r.stdout, r"style\s+required\s+FAIL")
        r = project_cmd(self.project, self.home, "task", "done", "TASK-0002", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not closed: a required check", r.stdout + r.stderr)
        self.assertTrue((self.project / "docs" / "road-map" / "going-on" / "TASK-0002-break-the-style.md").exists())
        r = project_cmd(self.project, self.home, "task", "done", "TASK-0002", "--force")
        done = next((self.project / "docs" / "road-map" / "completed").rglob("TASK-0002-*.md"))
        self.assertIn("CLOSED WITH --force", done.read_text(encoding="utf-8"))
        self.assertIn("pass", project_cmd(self.project, self.home, "check", "--step", "docs").stdout)

    def test_a_task_may_carry_its_own_policy(self):
        project_cmd(self.project, self.home, "policy", "use", "minimal")
        project_cmd(self.project, self.home, "task", "new", "Urgent fix")
        f = self.project / "docs" / "road-map" / "pending" / "next" / "TASK-0002-urgent-fix.md"
        f.write_text(re.sub(r"(?m)^policy:.*$", "policy: hotfix", f.read_text(encoding="utf-8")), encoding="utf-8")
        r = project_cmd(self.project, self.home, "check", "--task", "TASK-0002")
        self.assertIn("policy: hotfix (task", r.stdout)
        self.assertRegex(r.stdout, r"security\s+required\s+pass")
        project_cmd(self.project, self.home, "task", "start", "TASK-0002")
        r = project_cmd(self.project, self.home, "task", "done", "TASK-0002")
        self.assertIn("policy: hotfix (task", r.stdout)

    def test_custom_policy_with_its_own_check(self):
        pol = self.project / ".aix" / "custom" / "policies"
        pol.mkdir(parents=True)
        (pol / "ours.yaml").write_text("description: Our cycle\norder: [lint, docs, review]\nrequired: [lint, docs]\nadvised: [review]\nchecks:\n  lint: python3 -c \"import sys; sys.exit(0)\"\n", encoding="utf-8")
        project_cmd(self.project, self.home, "policy", "use", "ours")
        r = project_cmd(self.project, self.home, "check")
        self.assertRegex(r.stdout, r"lint\s+required\s+pass\s+python3")
        self.assertRegex(r.stdout, r"review\s+advised\s+skill review-code-review")
        self.assertIn("(config, project layer)", r.stdout)
        (pol / "ours.yaml").write_text("description: Our cycle\norder: [lint]\nrequired: [lint]\nchecks:\n  lint: python3 -c \"import sys; sys.exit(3)\"\n", encoding="utf-8")
        r = project_cmd(self.project, self.home, "check", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertRegex(r.stdout, r"lint\s+required\s+FAIL")


class LayerDefault(unittest.TestCase):
    def test_org_defaults_yaml_sets_the_policy_and_config_wins(self):
        home = temp_home(self)
        fork = make_fork(home, org=ACME)
        (fork / ".aix" / "org" / "defaults.yaml").write_text("policy: standard\n", encoding="utf-8")
        (fork / ".aix" / "org" / "policies").mkdir()
        (fork / ".aix" / "org" / "policies" / "standard.yaml").write_text("description: ACME standard, docs only\norder: [docs]\nrequired: [docs]\n", encoding="utf-8")
        project = home / "app"
        install(home, project, kit=fork)
        out = project_cmd(project, home, "policy").stdout
        self.assertRegex(out, r"(?m)^\* standard\s+org\s+ACME standard")
        self.assertIn("(org)", out)
        self.assertIn("Policy `standard` (org)", agents_md(project))
        r = project_cmd(project, home, "check")
        self.assertIn("(org, org layer)", r.stdout)
        project_cmd(project, home, "policy", "use", "freedom")
        self.assertIn("policy: anarchy (config)", project_cmd(project, home, "check").stdout, "the project's own line wins over the organisation's default")
        upgrade(project, home, kit=fork)
        self.assertRegex(config(project), r"(?m)^policy: anarchy")


if __name__ == "__main__":
    unittest.main()
