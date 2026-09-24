"""15. Seats for several agents: claim, release, whoami, list, total and lease; dead-process takeover; expired seats
elsewhere only with --force; a full table refused; task claims, refusals, --force; scope overlaps; one STATE per seat."""
import os, re, unittest
from helpers import assert_healthy, config, install, project_cmd, run, temp_home, upgrade

HERE = str(os.getpid())   # the test runner: alive for the whole test, so its sessions are live


def agent(project, home, session, *args, check=True, **who):
    """Run an aix command as a given session (AIX_SESSION identifies it; the pid decides liveness on this host).
    who: host (default lab), pid (default this runner, alive), tool (default claude)."""
    who = {"host": "lab", "pid": HERE, "tool": "claude", **who}
    env_extra = {"AIX_SESSION": session, "AIX_SESSION_PID": who["pid"], "AIX_TOOL": who["tool"], "AIX_HOST": who["host"]}
    return run(args, cwd=project, home=home, check=check, extra_env=env_extra)


def seat_file(project, name):
    return project / "docs" / "road-map" / "going-on" / "agents" / f"{name}.md"


class Seats(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        install(self.home, self.project)
        agent(self.project, self.home, "s0", "agent", "set", "total", "2")

    def test_settings(self):
        self.assertEqual(agent(self.project, self.home, "s0", "agent", "get", "total").stdout.strip(), "2")
        self.assertEqual(agent(self.project, self.home, "s0", "agent", "get", "lease").stdout.strip(), "4h")
        agent(self.project, self.home, "s0", "agent", "set", "lease", "30m")
        self.assertEqual(agent(self.project, self.home, "s0", "agent", "get", "lease").stdout.strip(), "30m")
        self.assertRegex(config(self.project), r"(?m)^agents_total: 2")
        r = agent(self.project, self.home, "s0", "agent", "set", "total", "0", check=False)
        self.assertNotEqual(r.returncode, 0)

    def test_claim_release_whoami_list(self):
        self.assertIn("no seat", agent(self.project, self.home, "s1", "agent", "whoami").stdout)
        r = agent(self.project, self.home, "s1", "agent", "claim")
        self.assertIn("agent-001: yours", r.stdout)
        self.assertEqual(agent(self.project, self.home, "s1", "agent", "whoami").stdout.strip(), "agent-001")
        self.assertIn("agent-001: yours", agent(self.project, self.home, "s1", "agent", "claim").stdout, "claiming again keeps the same seat")
        self.assertIn("agent-002: yours", agent(self.project, self.home, "s2", "agent", "claim", tool="opencode").stdout)
        listing = agent(self.project, self.home, "s1", "agent", "list").stdout
        self.assertRegex(listing, r"agent-001\s+live \(you\)\s+claude")
        self.assertRegex(listing, r"agent-002\s+live\s+opencode")
        self.assertTrue(seat_file(self.project, "agent-002").exists())
        r = agent(self.project, self.home, "s3", "agent", "claim", check=False)
        self.assertNotEqual(r.returncode, 0, "the table is full")
        self.assertIn("all 2 seats are taken", r.stdout + r.stderr)
        self.assertIn("agent-001: claude", r.stdout + r.stderr)
        agent(self.project, self.home, "s2", "agent", "release")
        self.assertFalse(seat_file(self.project, "agent-002").exists())
        self.assertIn("agent-002: yours", agent(self.project, self.home, "s3", "agent", "claim").stdout)
        r = agent(self.project, self.home, "s9", "agent", "release", check=False)
        self.assertNotEqual(r.returncode, 0, "a session without a seat cannot release")

    def test_dead_process_seat_is_taken_over_here(self):
        agent(self.project, self.home, "s1", "agent", "claim", pid="999999")   # a process that does not exist
        agent(self.project, self.home, "s2", "agent", "claim", pid="999998")
        listing = agent(self.project, self.home, "s3", "agent", "list").stdout
        self.assertRegex(listing, r"agent-001\s+dead")
        d = agent(self.project, self.home, "s3", "doctor", check=False).stdout
        self.assertIn("seat agent-001 is dead", d)
        r = agent(self.project, self.home, "s3", "agent", "claim")
        self.assertIn("agent-001: yours, taken over: its process is gone", r.stdout)
        text = seat_file(self.project, "agent-001").read_text(encoding="utf-8")
        self.assertIn("took_over:", text)

    def test_expired_seat_elsewhere_needs_force(self):
        agent(self.project, self.home, "r1", "agent", "claim", host="other-laptop")
        agent(self.project, self.home, "r2", "agent", "claim", host="other-laptop")
        r = agent(self.project, self.home, "s1", "agent", "claim", check=False)
        self.assertNotEqual(r.returncode, 0, "fresh heartbeats on another machine: nothing to take")
        f = seat_file(self.project, "agent-001")
        f.write_text(re.sub(r"(?m)^heartbeat:.*$", "heartbeat: 2020-01-01T00:00:00Z", f.read_text(encoding="utf-8")), encoding="utf-8")
        self.assertRegex(agent(self.project, self.home, "s1", "agent", "list").stdout, r"agent-001\s+expired")
        r = agent(self.project, self.home, "s1", "agent", "claim", check=False)
        self.assertNotEqual(r.returncode, 0, "expired elsewhere: not without --force")
        self.assertIn("--force", r.stdout + r.stderr)
        r = agent(self.project, self.home, "s1", "agent", "claim", "--force")
        self.assertIn("agent-001: yours, taken over", r.stdout)

    def test_shrinking_below_taken_seats_is_refused(self):
        agent(self.project, self.home, "s1", "agent", "claim")
        agent(self.project, self.home, "s2", "agent", "claim")
        r = agent(self.project, self.home, "s0", "agent", "set", "total", "1", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("agent-002 still taken", r.stdout + r.stderr)


class TasksAndSeats(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        install(self.home, self.project)
        agent(self.project, self.home, "s0", "agent", "set", "total", "3")
        for title in ("Orders endpoint", "Orders repository", "Billing report"):
            agent(self.project, self.home, "s0", "task", "new", title)
        nxt = self.project / "docs" / "road-map" / "pending" / "next"
        for f, scope in ((nxt / "TASK-0002-orders-endpoint.md", "[backend/app/orders/**]"), (nxt / "TASK-0003-orders-repository.md", "[backend/app/orders/repository.py]"), (nxt / "TASK-0004-billing-report.md", "[backend/app/billing/**]")):
            f.write_text(re.sub(r"(?m)^scope:.*$", f"scope: {scope}", f.read_text(encoding="utf-8")), encoding="utf-8")

    def test_start_claims_signs_refuses_and_forces(self):
        r = agent(self.project, self.home, "s1", "task", "start", "TASK-0002")
        self.assertIn("(agent-001)", r.stdout, "a seat is claimed by itself")
        task = self.project / "docs" / "road-map" / "going-on" / "TASK-0002-orders-endpoint.md"
        text = task.read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^owner: agent-001")
        self.assertRegex(text, r"(?m)^claimed: \d{4}-")
        self.assertRegex(text, r"(?m)^claimed_by: claude \S+@lab")
        r = agent(self.project, self.home, "s2", "task", "start", "TASK-0002", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("is held by agent-001", r.stdout + r.stderr)
        r = agent(self.project, self.home, "s2", "task", "start", "TASK-0002", "--force")
        self.assertIn("(agent-002)", r.stdout)
        self.assertRegex(task.read_text(encoding="utf-8"), r"(?m)^owner: agent-002")
        listing = agent(self.project, self.home, "s1", "task", "list").stdout
        self.assertRegex(listing, r"TASK-0002\s+going-on\s+agent-002")

    def test_scope_overlap_is_warned_at_start_and_in_list(self):
        agent(self.project, self.home, "s1", "task", "start", "TASK-0002")
        r = agent(self.project, self.home, "s2", "task", "start", "TASK-0003")
        self.assertIn("warning: scope overlaps TASK-0002 (agent-001)", r.stdout)
        r = agent(self.project, self.home, "s3", "task", "start", "TASK-0004")
        self.assertNotIn("warning", r.stdout, "billing does not overlap orders")
        listing = agent(self.project, self.home, "s1", "task", "list").stdout
        self.assertIn("overlap: TASK-0002 and TASK-0003", listing)
        self.assertNotIn("TASK-0004 touch", listing)

    def test_one_state_per_seat_and_the_overview(self):
        going = self.project / "docs" / "road-map" / "going-on"
        agent(self.project, self.home, "s1", "task", "start", "TASK-0002")
        agent(self.project, self.home, "s2", "task", "start", "TASK-0004", tool="opencode")
        self.assertRegex((going / "STATE-agent-001.md").read_text(encoding="utf-8"), r"(?m)^active_task: TASK-0002")
        self.assertRegex((going / "STATE-agent-002.md").read_text(encoding="utf-8"), r"(?m)^active_task: TASK-0004")
        overview = (going / "STATE.md").read_text(encoding="utf-8")
        self.assertIn("several agents share this repository", overview)
        self.assertRegex(overview, r"\| agent-001 \| live \| claude .* \| TASK-0002 \|")
        self.assertRegex(overview, r"\| agent-002 \| live \| opencode .* \| TASK-0004 \|")
        agent(self.project, self.home, "s1", "task", "done", "TASK-0002")
        self.assertRegex((going / "STATE-agent-001.md").read_text(encoding="utf-8"), r"(?m)^active_task: none")
        self.assertRegex((going / "STATE.md").read_text(encoding="utf-8"), r"\| agent-001 \| live \| claude .* \| none \|")
        assert_healthy(self, self.project, self.home)

    def test_single_seat_project_keeps_the_classic_state(self):
        agent(self.project, self.home, "s0", "agent", "set", "total", "1")
        going = self.project / "docs" / "road-map" / "going-on"
        agent(self.project, self.home, "s1", "task", "start", "TASK-0002")
        self.assertRegex((going / "STATE.md").read_text(encoding="utf-8"), r"(?m)^active_task: TASK-0002")
        self.assertFalse((going / "STATE-agent-001.md").exists())
        self.assertNotIn("several agents", (going / "STATE.md").read_text(encoding="utf-8"))

    def test_doctor_flags_a_task_held_by_a_dead_seat_and_upgrade_keeps_the_total(self):
        agent(self.project, self.home, "s1", "task", "start", "TASK-0002", pid="999999")
        d = agent(self.project, self.home, "s2", "doctor", check=False).stdout
        self.assertIn("TASK-0002 is going-on but its owner agent-001 is not a live seat", d)
        upgrade(self.project, self.home)
        self.assertRegex(config(self.project), r"(?m)^agents_total: 3")


if __name__ == "__main__":
    unittest.main()
