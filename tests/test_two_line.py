"""21. Assembled, then used: `aix code security` reports a string built from a literal plus a value on one line and
passed to a dangerous call within the next 40 lines, in Python, JS/TS, Java and Rust. The literal decides the sinks:
SQL, path, HTML, template, URL; shell and eval take any. Every FIND line is reported with its CWE, every other line
is clean: no `+`, a reassignment in between, a harmless callee, an argument list, beyond the reach."""
import re, unittest
from helpers import install, project_cmd, temp_home

PY = '''
import os, subprocess, requests
from flask import Markup, render_template_string
from jinja2 import Template

def shell(name):
    cmd = "ls " + name
    os.system(cmd)                                          # FIND:CWE-78
    cmd2 = f"ls {name}"
    subprocess.run(cmd2, shell=True)                        # FIND:CWE-78
    cmd3 = "ls {}".format(name)
    subprocess.run(cmd3, shell=True)                        # FIND:CWE-78
    cmd4 = "ls %s" % name
    subprocess.check_output(cmd4, shell=True)               # FIND:CWE-78
    subprocess.run(["ls", name])                            # SAFE: argument list
    cmd5 = "ls " + name
    subprocess.run(cmd5)                                    # SAFE: no shell
    cmd6 = "ls " + name
    cmd6 = shlex.quote(cmd6)
    os.system(cmd6)                                         # SAFE: reassigned in between
    fixed = "ls -la"
    os.system(fixed)                                        # SAFE: no value assembled in

def code(expr):
    src = "1 + " + expr
    eval(src)                                               # FIND:CWE-95
    exec(src)                                               # FIND:CWE-95

def files(name):
    path = "/srv/files/" + name
    open(path)                                              # FIND:CWE-22
    path2 = os.path.join(BASE, name)
    send_file(path2)                                        # FIND:CWE-22
    label = "file: " + name
    open(label)                                             # SAFE: the literal is not a path
    log("opened " + name)                                   # SAFE: no sink

def web(name, url):
    html = "<b>" + name + "</b>"
    return Markup(html)                                     # FIND:CWE-79

def tpl(name):
    text = "Hello {{ " + name + " }}"
    Template(text).render()                                 # FIND:CWE-1336
    render_template_string(text)                            # FIND:CWE-1336

def fetch(host):
    target = "https://" + host + "/api"
    requests.get(target)                                    # FIND:CWE-918
    q = "SELECT * FROM t WHERE id = " + host
    cur.execute(q)                                          # FIND:CWE-89
    cur.execute("SELECT * FROM t WHERE id = ?", (host,))    # SAFE: parameterised
'''

JS = '''
const { exec, spawn } = require("child_process");
const fs = require("fs");
function run(name) {
  const cmd = "ls " + name;
  exec(cmd);                                                // FIND:CWE-78
  const cmd2 = `ls ${name}`;
  spawn(cmd2, { shell: true });                             // FIND:CWE-78
  spawn("ls", [name]);                                      // SAFE: argument list
  const cmd3 = "ls " + name;
  spawn(cmd3);                                              // SAFE: no shell
  let src = "return " + name;
  new Function(src);                                        // FIND:CWE-95
}
function files(name) {
  const p = "/srv/" + name;
  fs.readFileSync(p);                                       // FIND:CWE-22
  const p2 = path.join(BASE, name);
  fs.createReadStream(p2);                                  // FIND:CWE-22
  const html = "<i>" + name + "</i>";
  el.innerHTML = html;                                      // FIND:CWE-79
  res.send(html);                                           // FIND:CWE-79
  const url = `https://${name}.example.com/`;
  fetch(url);                                               // FIND:CWE-918
  const sql = `SELECT * FROM t WHERE n = ${name}`;
  db.query(sql);                                            // FIND:CWE-89
  const msg = "hello " + name;
  console.log(msg);                                         // SAFE: no sink
}
'''

JAVA = '''
package com.acme;
public class Cmd {
    void run(String name) throws Exception {
        String cmd = "ls " + name;
        Runtime.getRuntime().exec(cmd);                     // FIND:CWE-78
        String cmd2 = String.format("ls %s", name);
        new ProcessBuilder(cmd2).start();                   // FIND:CWE-78
        String p = "/srv/" + name;
        new File(p);                                        // FIND:CWE-22
        String p2 = "/srv/" + name;
        Files.readAllBytes(Paths.get(p2));                  // FIND:CWE-22
        String q = "SELECT * FROM t WHERE n = " + name;
        stmt.executeQuery(q);                               // FIND:CWE-89
        String u = "https://" + name + "/x";
        new URL(u);                                         // FIND:CWE-918
        String html = "<b>" + name + "</b>";
        response.getWriter().print(html);                   // FIND:CWE-79
        String label = "user " + name;
        logger.info(label);                                 // SAFE: no sink
    }
}
'''

RS = '''
use std::process::Command;
use std::fs::File;
fn run(name: &str) {
    let cmd = format!("ls {}", name);
    Command::new("sh").arg("-c").arg(&cmd).status();        // FIND:CWE-78
    let cmd2 = format!("ls {}", name);
    Command::new("ls").arg(&cmd2).status();                 // SAFE: no shell
    let p = format!("/srv/{}", name);
    File::open(&p);                                         // FIND:CWE-22
    let u = format!("https://{}/x", name);
    reqwest::blocking::get(&u);                             // FIND:CWE-918
    let msg = format!("hello {}", name);
    println!("{}", msg);                                    // SAFE: no sink
}
'''

FAR = "\n" + "def far(name):\n    cmd = 'ls ' + name\n" + "    x = 1\n" * 45 + "    os.system(cmd)                                          # SAFE: beyond the 40-line reach\n"
ACCEPTED = '''
def ok(name):
    cmd = "ls " + name
    os.system(cmd)   # FIND:CWE-78 aix: accepted VUL-INJ-002 reviewed, name is an enum value
'''
SAMPLES = {"shapes.py": PY, "shapes.js": JS, "Cmd.java": JAVA, "shapes.rs": RS, "far.py": FAR, "accepted.py": ACCEPTED}


def expected(src: str) -> dict:
    return {i: m.group(1) for i, line in enumerate(src.splitlines(), 1) for m in [re.search(r"FIND:(CWE-\d+)", line)] if m}


class AssembledThenUsed(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        (self.project / "src").mkdir(parents=True)
        for name, src in SAMPLES.items():
            (self.project / "src" / name).write_text(src, encoding="utf-8")
        install(self.home, self.project)

    def report(self, name: str) -> str:
        return project_cmd(self.project, self.home, "code", "security", f"src/{name}").stdout

    def found(self, name: str, out: str) -> dict:
        rx = rf"src/{re.escape(name)}:(\d+)  [^\n]*(?:assembled|built) from strings[^\n]*\((CWE-\d+)\)"
        return {int(m.group(1)): m.group(2) for m in re.finditer(rx, out)}

    def check(self, name):
        out = self.report(name)
        self.assertEqual(self.found(name, out), expected(SAMPLES[name]), f"\n{out}")

    def test_python(self):
        self.check("shapes.py")

    def test_javascript(self):
        self.check("shapes.js")

    def test_java(self):
        self.check("Cmd.java")

    def test_rust(self):
        self.check("shapes.rs")

    def test_reach_and_accepted(self):
        self.check("far.py")
        self.check("accepted.py")
        self.assertRegex(self.report("accepted.py"), r"accepted\.py:4  [^\n]*\[accepted: VUL-INJ-002 reviewed, name is an enum value\]")

    def test_snippet_names_both_lines(self):
        self.assertRegex(self.report("shapes.py"), r'cmd = "ls " \+ name  \.\.\.  os\.system\(cmd\)')


if __name__ == "__main__":
    unittest.main()
