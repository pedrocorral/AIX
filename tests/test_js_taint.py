"""20. JS/TS taint: `aix code vulnerabilities --taint` follows input from Express, Koa, Next, Node CLI and browser
sources to shell, eval, file, SQL, redirect, HTML and outbound-request sinks. Every line marked FIND:CWE-nn must be
reported with that CWE, every other line must not; sanitisers, parameterised queries, argument lists, constants and
callbacks are the negatives. Accepted markers and test files keep their tags; Python results do not change."""
import re, unittest
from helpers import install, project_cmd, temp_home

EXPRESS = '''
const express = require("express");
const { exec, execSync, spawn, execFile } = require("child_process");
const fs = require("fs");
const path = require("path");
const validator = require("validator");
const app = express();
const BASE = "/srv/files";

app.get("/run", (req, res) => {
  const cmd = req.query.cmd;
  exec("ls " + cmd);                                            // FIND:CWE-78
  execSync(`ls ${cmd}`);                                        // FIND:CWE-78
  spawn("ls", [cmd]);                                           // SAFE: argument list, no shell
  spawn("ls", [cmd], { shell: true });                          // FIND:CWE-78
  execFile("ls", [cmd]);                                        // SAFE
  const n = Number(req.query.n);
  exec("sleep " + n);                                           // SAFE: sanitised
  exec("ls " + parseInt(cmd, 10));                              // SAFE: sanitised inline
  res.send("ok");                                               // SAFE: constant
});

app.get("/file", (req, res) => {
  const { name } = req.query;
  fs.readFile(path.join(BASE, name), () => {});                 // FIND:CWE-22
  const safe = path.basename(name);
  fs.readFileSync(path.join(BASE, safe));                       // SAFE: basename
  res.sendFile(name);                                           // FIND:CWE-22
  fs.readFileSync("/etc/hosts");                                // SAFE: constant
  fs.promises.readFile(                                         // FIND:CWE-22 (the statement spans lines; reported at the call)
    path.join(BASE, name)
  );
});

app.post("/user", async (req, res) => {
  const { id, bio } = req.body;
  await db.query(`SELECT * FROM users WHERE id = ${id}`);       // FIND:CWE-89
  const sql = "SELECT * FROM users WHERE id = " + id;
  await db.query(sql);                                          // FIND:CWE-89
  await db.query("SELECT * FROM users WHERE id = ?", [id]);     // SAFE: parameterised
  await prisma.$queryRawUnsafe("SELECT " + bio);                // FIND:CWE-89
  await prisma.user.findMany({ where: { id } });                // SAFE: no SQL sink
  res.send("<b>" + bio + "</b>");                               // FIND:CWE-79
  res.send("<b>" + validator.escape(bio) + "</b>");             // SAFE: escaped
  res.json({ bio });                                            // SAFE: JSON
});

app.get("/go", (req, res) => {
  res.redirect(req.query.next);                                 // FIND:CWE-601
  res.redirect("/home");                                        // SAFE: constant
  const back = req.query.back || "/";
  res.redirect(back);                                           // FIND:CWE-601
});

app.get("/proxy", async (req, res) => {
  const url = req.query.url;
  const r = await fetch(url);                                   // FIND:CWE-918
  const r2 = await axios.get("https://api.example.com/?q=" + encodeURIComponent(url));   // SAFE: encoded
  const r3 = await fetch("https://api.example.com/health");     // SAFE: constant
  eval(req.query.code);                                         // FIND:CWE-95
  new Function(req.body.fn);                                    // FIND:CWE-95
  setTimeout("run(" + url + ")", 10);                           // FIND:CWE-95
  setTimeout(() => run(url), 10);                               // SAFE: callback
  const cleaned = url.trim();
  const r4 = await fetch(cleaned);                              // FIND:CWE-918 (a method call keeps the taint)
});

function helper(target) {
  exec(target);                                                 // FIND:CWE-78 (reached through the call below)
}
const runIt = (what) => {
  execSync(what);                                               // FIND:CWE-78 (arrow function, reached through the call below)
};
app.get("/h", (req, res) => {
  helper(req.query.t);
  runIt(req.query.w);
  const local = "constant";
  exec(local);                                                  // SAFE: constant
  const cmd = "echo";
  exec(cmd);                                                    // SAFE: cmd is a new, clean variable in this scope
});

app.get("/scope", (req, res) => {
  const tmp = req.query.tmp;
  if (tmp) {
    const inner = tmp + ".log";
    fs.unlinkSync(inner);                                       // FIND:CWE-22
  }
  fs.unlinkSync("/var/log/app.log");                            // SAFE: constant
});
const home = process.env.HOME;
fs.readFileSync(home + "/config");                              // FIND:CWE-22 (process.env is input)
exec("id " + req.query.who);   // FIND:CWE-78 aix: accepted VUL-INJ-002 demo of the marker
'''

NEXT = '''
import { NextRequest, NextResponse } from "next/server";
import { redirect } from "next/navigation";
import { readFile } from "fs/promises";

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get("q");
  const data = await readFile(`/data/${q}.json`);               // FIND:CWE-22
  const page: number = parseInt(q ?? "0", 10);
  await readFile(`/data/${page}.json`);                          // SAFE: parseInt
  const target = request.nextUrl.searchParams.get("to");
  if (target) redirect(target);                                  // FIND:CWE-601
  redirect("/login");                                            // SAFE: constant
  return NextResponse.json({ ok: true });
}

export async function POST(request: Request) {
  const body = await request.json();
  const rows = await sql.raw(`DELETE FROM t WHERE id = ${body.id}`);   // FIND:CWE-89
  const upstream = await fetch(body.url);                        // FIND:CWE-918
  const form = await request.formData();
  const file = form.get("file");
  await readFile(file);                                          // FIND:CWE-22
  return NextResponse.json(rows);
}
'''

REACT = '''
import DOMPurify from "dompurify";

export function Profile({ html }: { html: string }) {
  const params = new URLSearchParams(window.location.search);
  const name = params.get("name");
  const clean = DOMPurify.sanitize(name);
  return (
    <div>
      <div dangerouslySetInnerHTML={{ __html: name }} />          // FIND:CWE-79
      <div dangerouslySetInnerHTML={{ __html: clean }} />         // SAFE: DOMPurify
      <div dangerouslySetInnerHTML={{ __html: html }} />          // SAFE: a prop is not an input source here
      <p>{name}</p>
    </div>
  );
}

export function go() {
  const hash = location.hash.slice(1);
  document.getElementById("out").innerHTML = "<i>" + hash + "</i>";     // FIND:CWE-79
  document.getElementById("out").textContent = hash;                      // SAFE: text
  location.href = hash;                                                   // FIND:CWE-601
  window.open(new URLSearchParams(location.search).get("u"));             // FIND:CWE-601
  document.write(document.referrer);                                      // FIND:CWE-79
  el.insertAdjacentHTML("beforeend", hash);                               // FIND:CWE-79
  el.innerHTML = "<b>static</b>";                                         // SAFE: constant
  if (hash === "x") {                                                     // SAFE: a comparison is not an assignment
    console.log(hash);
  }
}
'''

CLI = '''
import fs from "fs";
import { execSync, spawnSync } from "child_process";
const file = process.argv[2];
fs.writeFileSync(file, "x");                                     // FIND:CWE-22
const port = parseInt(process.argv[3]);
const out = `/tmp/${port}.log`;
fs.writeFileSync(out, "x");                                      // SAFE: parseInt
execSync(`git log ${process.env.BRANCH}`);                       // FIND:CWE-78
spawnSync("git", ["log", process.env.BRANCH]);                   // SAFE: argument list
for (const arg of process.argv) {
  execSync("echo " + arg);                                       // FIND:CWE-78 (loop variable over input)
}
'''

KOA = '''
const shellQuote = require("shell-quote");
router.get("/k", async (ctx) => {
  const { id } = ctx.request.body;
  await knex.raw("select " + id);                                // FIND:CWE-89
  ctx.redirect(ctx.query.back);                                  // FIND:CWE-601
  exec("ls " + shellQuote.quote([ctx.query.d]));                 // SAFE: quoted
  ctx.body = ctx.query.msg;                                      // SAFE: not a sink the tool knows
});
'''

TEST_FILE = '''
const { exec } = require("child_process");
test("x", () => {
  exec("ls " + process.env.DIR);                                 // FIND:CWE-78 (listed as test, not gated)
});
'''

PY = '''
import subprocess
from flask import request
@app.route("/p")
def p():
    subprocess.run("ls " + request.args.get("d"), shell=True)   # FIND:CWE-78
'''

SAMPLES = {"server.js": EXPRESS, "route.ts": NEXT, "Profile.tsx": REACT, "cli.mjs": CLI, "koa.js": KOA, "__tests__/x.test.js": TEST_FILE, "app.py": PY}


def expected(src: str) -> dict:
    """line -> CWE for every line marked FIND."""
    return {i: m.group(1) for i, line in enumerate(src.splitlines(), 1) for m in [re.search(r"FIND:(CWE-\d+)", line)] if m}


class JsTaint(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        for name, src in SAMPLES.items():
            (self.project / "src" / name).parent.mkdir(parents=True, exist_ok=True)
            (self.project / "src" / name).write_text(src, encoding="utf-8")
        install(self.home, self.project)
        self.out = project_cmd(self.project, self.home, "code", "vulnerabilities", "--taint", "src").stdout

    def found(self, name: str) -> dict:
        return {int(m.group(1)): m.group(2) for m in re.finditer(rf"src/{re.escape(name)}:(\d+)  input reaches [^(]+\((CWE-\d+)\)", self.out)}

    def check(self, name):
        self.assertEqual(self.found(name), expected(SAMPLES[name]), f"\n{self.out}")

    def test_express(self):
        self.check("server.js")

    def test_next(self):
        self.check("route.ts")

    def test_react_and_browser(self):
        self.check("Profile.tsx")

    def test_node_cli(self):
        self.check("cli.mjs")

    def test_koa(self):
        self.check("koa.js")

    def test_tags_and_python_untouched(self):
        narrowed = project_cmd(self.project, self.home, "code", "vulnerabilities", "--taint", "src/__tests__").stdout
        self.assertRegex(narrowed, r"x\.test\.js:4  [^\n]*\[test\]")
        self.assertRegex(self.out, r"\.\.\. \d+ more \(narrow the path", "a register row shows 20 findings and says how many it hides")
        self.assertRegex(self.out, r"server\.js:\d+  [^\n]*\[accepted: demo of the marker\]")
        self.check("app.py")
        self.assertIn("taint paths (Python, JS/TS)", self.out)

    def test_gate_counts_only_live_findings(self):
        r = project_cmd(self.project, self.home, "code", "vulnerabilities", "--taint", "--gate", "src", check=False)
        n = sum(len(expected(s)) for s in SAMPLES.values()) - 2   # the test file and the accepted line
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"GATE FAILED: {n} finding(s) to review", r.stderr, r.stdout + r.stderr)
        clean = project_cmd(self.project, self.home, "code", "vulnerabilities", "--taint", "--gate", "src/koa.js", check=False)
        self.assertIn("GATE FAILED: 2 finding(s)", clean.stderr)


if __name__ == "__main__":
    unittest.main()
