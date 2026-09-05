#!/usr/bin/env python3
"""Road-map helper: create / start / finish tasks and keep going-on/STATE.md in sync.
  roadmap.py new "Title" [--bucket next|backlog|ideas]   -> pending/<bucket>/TASK-0007-title.md
  roadmap.py start TASK-0007                              -> moves to going-on/, sets status, updates STATE.md
  roadmap.py block TASK-0007 "reason"                    -> moves to blocked/, clears active_task
  roadmap.py done  TASK-0007                              -> moves to completed/YYYY-MM/, stamps completion
  roadmap.py list                                         -> one-line summary of every task"""
import re, sys, shutil, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RM = ROOT / "docs" / "road-map"
TEMPLATE = ROOT / "templates" / "task.md"


def all_tasks():
    return sorted(RM.rglob("TASK-*.md"))


def next_id():
    ids = [int(m.group(1)) for p in all_tasks() if (m := re.match(r"TASK-(\d{4})", p.name))]
    return f"TASK-{(max(ids) + 1 if ids else 1):04d}"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:50]


def set_field(text, key, value):
    return re.sub(rf"^{key}:.*$", f"{key}: {value}", text, count=1, flags=re.M)


def find(tid):
    for p in all_tasks():
        if p.name.startswith(tid):
            return p
    sys.exit(f"{tid} not found")


def cmd_new(title, bucket="next"):
    tid = next_id()
    dst = RM / "pending" / bucket / f"{tid}-{slug(title)}.md"
    t = TEMPLATE.read_text(encoding="utf-8")
    t = set_field(t, "id", tid); t = set_field(t, "title", title)
    t = set_field(t, "created", datetime.date.today().isoformat())
    dst.write_text(t, encoding="utf-8"); print(dst.relative_to(ROOT))


def cmd_start(tid):
    p = find(tid); dst = RM / "going-on" / p.name
    t = set_field(p.read_text(encoding="utf-8"), "status", "going-on")
    dst.write_text(t, encoding="utf-8"); p.unlink()
    state = RM / "going-on" / "STATE.md"
    s = state.read_text(encoding="utf-8")
    s = set_field(s, "active_task", tid); s = set_field(s, "updated", datetime.datetime.now().isoformat(timespec="minutes"))
    state.write_text(s, encoding="utf-8"); print(dst.relative_to(ROOT))


def cmd_block(tid, reason=""):
    p = find(tid); dst = RM / "blocked" / p.name
    t = set_field(p.read_text(encoding="utf-8"), "status", "blocked")
    t = t.replace("## Decisions / open questions\n", f"## Decisions / open questions\n- BLOCKED {datetime.date.today().isoformat()}: {reason}\n", 1)
    dst.write_text(t, encoding="utf-8"); p.unlink()
    state = RM / "going-on" / "STATE.md"; s = state.read_text(encoding="utf-8")
    if re.search(rf"^active_task:\s*{tid}", s, re.M): s = set_field(s, "active_task", "none")
    state.write_text(s, encoding="utf-8"); print(dst.relative_to(ROOT))


def cmd_done(tid):
    p = find(tid); month = datetime.date.today().strftime("%Y-%m")
    dst = RM / "completed" / month / p.name; dst.parent.mkdir(parents=True, exist_ok=True)
    t = set_field(p.read_text(encoding="utf-8"), "status", "completed")
    t = set_field(t, "completed", datetime.date.today().isoformat())
    dst.write_text(t, encoding="utf-8"); p.unlink()
    state = RM / "going-on" / "STATE.md"
    s = state.read_text(encoding="utf-8")
    if re.search(rf"^active_task:\s*{tid}", s, re.M):
        s = set_field(s, "active_task", "none")
    state.write_text(s, encoding="utf-8"); print(dst.relative_to(ROOT))


def cmd_list():
    for p in all_tasks():
        t = p.read_text(encoding="utf-8")
        title = re.search(r"^title:\s*(.*)$", t, re.M); status = re.search(r"^status:\s*(.*)$", t, re.M)
        print(f"{p.name[:9]}  {status.group(1) if status else '?':10s}  {title.group(1) if title else p.name}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    if a[0] == "new": cmd_new(a[1], a[3] if len(a) > 3 and a[2] == "--bucket" else "next")
    elif a[0] == "start": cmd_start(a[1])
    elif a[0] == "block": cmd_block(a[1], a[2] if len(a) > 2 else "")
    elif a[0] == "done": cmd_done(a[1])
    elif a[0] == "list": cmd_list()
    else: sys.exit(__doc__)
