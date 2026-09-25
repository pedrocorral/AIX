"""The language samples of test_hygiene.py: every line marked FIND:kind must be reported with that kind by
`aix code style`, every other line must be clean. Kept apart from the test so each file stays under 400 lines."""

PY = '''
import os                                                   # FIND:leftover (unused import)
import sys
from json import dumps, loads                               # FIND:leftover (loads unused)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pathlib import Path                                # SAFE: used in an annotation string below


def uses(x: "Path"):
    print(sys.argv, dumps(x))


def leftover_variable(x):
    unused = x + 1                                          # FIND:leftover
    _ignored = x
    a, b = x, x                                             # SAFE: b is read
    return b


def leftover_parameter(x, unused):                          # FIND:leftover
    return x


def underscore_parameter(x, _unused):
    return x


def star_parameters(x, *args, **kwargs):
    return x


@app.route("/x")
def decorated(request, unused):
    return request


class Base:
    def method(self, x):
        raise NotImplementedError

    def hook(self, event):
        pass

    def override(self, x):
        return super().override(x)

    def real(self, x, unused):
        return x


def swallowed(x):
    try:
        return int(x)
    except ValueError:                                      # FIND:swallowed
        pass


def swallowed_ellipsis(x):
    try:
        return int(x)
    except ValueError:                                      # FIND:swallowed
        ...


def bare_except(x):
    try:
        return int(x)
    except:                                                 # FIND:swallowed (bare except catches SystemExit too)
        return 0


def intended(x):
    try:
        return int(x)
    except ValueError:
        # not a number: the caller gets None on purpose
        pass


def logged(x):
    try:
        return int(x)
    except ValueError:
        log.warning("not a number")


def mutable_default(items=[]):                              # FIND:bug
    return items


def mutable_dict(opts={}):                                  # FIND:bug
    return opts


def mutable_call(items=list()):                             # FIND:bug
    return items


def fine_defaults(items=None, name="x", pair=(1, 2)):
    return items, name, pair


class Hook:
    def get_max_age(self, filename):
        return 42

    def _private(self, unused):                             # FIND:leftover
        return 1


def reraises(x):
    try:
        return int(x)
    except:
        log.exception("failed")
        raise


def optional_dependency():
    try:
        import chardet
    except ImportError:
        pass
    return chardet


def fstring(name):
    return f"hello {name}"


def click_callback(ctx, param, value):
    return value


def test_fixture_params(app, client, monkeypatch):
    assert client


def positional_before_used(unused, x):
    return x


def records(monkeypatch):
    class Recorder:
        called = False

    def fake():
        Recorder.called = True

    monkeypatch.setattr("x.y", fake)
    return Recorder.called


class Resource:
    def __exit__(self, exc_type, exc_value, traceback):
        return False
'''

JS = '''
import fs from "fs";                                        // FIND:leftover
import React from "react";
export const View = () => <div />;
import { join, resolve } from "path";                       // FIND:leftover (resolve unused)
import "./polyfill";
const yaml = require("yaml");                               // FIND:leftover
const { readFile } = require("fs/promises");

export function uses(p) {
  return readFile(join(p, "x"));
}
function leftoverVariable(x) {
  const unused = x + 1;                                     // FIND:leftover
  let _skip = x;
  return x;
}
function leftoverParameter(x, unused) {                     // FIND:leftover
  return x;
}
function underscore(x, _event) {
  return x;
}
class Thing {
  hook(event) { }
  real(x, unused) {
    return x;
  }
}
app.get("/x", (req, res, next) => {
  res.send(req.query.q);
});
function swallowed(x) {
  try { return JSON.parse(x); } catch (e) { }               // FIND:swallowed
}
function swallowedPromise(p) {
  p.catch(() => {});                                        // FIND:swallowed
}
function intended(x) {
  try { return JSON.parse(x); } catch (e) { /* malformed input: null on purpose */ }
}
function logged(x) {
  try { return JSON.parse(x); } catch (e) { console.warn(e); }
}
function callbackNames(err, req, res, next) {
  res.send(err.message);
}
function templateUse(id) {
  const key = `${id}-key`;
  return `${key}`;
}
function spread(props) {
  return { ...props };
}
class Shape {
  area(unit) { return 1; }
}
function optionalParam(formState?: any) {
  return track(formState);
}
export const Text = () => <p>Don't strip me: {helper()}</p>;
function helper() {
  const label = "x";
  return label;
}
const Destructured = ({ style }) => {
  return style;
};
function positionalBeforeUsed(unused, x) {
  return x;
}
function laterDeclared() {
  const onKey = () => { indent(); return isDone; };
  const indent = () => 1;
  let isDone = false;
  el.innerHTML = "";
  node.innerHTML = svg.outerHTML;
  return onKey;
}
const Typed = ({ color, onClick, name, src }: Props) => {
  return color + onClick + name;
};
function assignmentInCondition(a, b) {
  if (a = b) { return 1; }                                  // FIND:bug
  while ((a = next())) { break; }
  if (a === b || a <= b || a >= b || a != b) { return 2; }
  const f = (x) => x;
  if (f(a) == b) { return 3; }
  return 0;
}
'''

RS = r'''
use std::collections::HashMap;                              // not checked: a Rust `use` may bring a trait into scope (the compiler warns)
use std::fs::{read_to_string, write};
use std::io::Result;

fn uses(p: &str) -> Result<String> {
    read_to_string(p)
}
fn leftover_variable(x: u8) -> u8 {
    let unused = x + 1;                                     // FIND:leftover
    let _skip = x;
    x
}
fn leftover_parameter(x: u8, unused: u8) -> u8 {            // FIND:leftover
    x
}
fn underscore(x: u8, _ctx: u8) -> u8 {
    x
}
impl Handler for Thing {
    fn handle(&self, event: Event) -> bool {
        true
    }
}
fn todo_body(x: u8) -> u8 {
    todo!()
}
fn format_use(tag: &str) -> String {
    format!(r"\{tag}{{")
}
fn raw_string_then_use(args: Vec<u8>) -> usize {
    let sep = r"\";
    args.len() + sep.len()
}
fn generic_params<'a>(mapping: Vec<(&'a str, Target<'a>)>, count: usize) -> usize {
    mapping.len() + count
}
pub fn public_api(x: u8, hint: u8) -> u8 {
    x
}
#[cfg(not(unix))]
fn from_entry_os(depth: usize, ent: &Entry) -> Result<u8, Error> {
    Err(Error::new("unsupported platform"))
}
fn range_use(version: &str) -> usize {
    let end = version.find(' ').unwrap_or(0);
    version[..end].len()
}
fn if_let_pattern(ctx: Ctx) -> u8 {
    if let ContextMode::Limited(ref limited) = ctx.mode {
        return limited.get();
    }
    while let Some(next) = ctx.next() {
        return next;
    }
    0
}
'''

JAVA = '''
package com.acme;
import java.util.List;                                      // FIND:leftover
import java.util.Map;
import java.util.Arrays;
import java.io.IOException;                                 // FIND:leftover
public class Thing {
    String m;
    int leftoverVariable(int x) {
        int unused = x + 1;                                 // FIND:leftover
        return x;
    }
    private int leftoverParameter(int x, int unused) {      // FIND:leftover
        return x;
    }
    @Override
    public void handle(Event event) {
    }
    public void hook(Event event) { }
    abstract void abstractOne(int x);
    void unsupported(int x) { throw new UnsupportedOperationException(); }
    int swallowed(String x) {
        try { return Integer.parseInt(x); } catch (NumberFormatException e) { }   // FIND:swallowed
        return 0;
    }
    int swallowedIgnored(String x) {
        try { return Integer.parseInt(x); } catch (NumberFormatException ignored) { }   // FIND:swallowed
        return 0;
    }
    int intended(String x) {
        try { return Integer.parseInt(x); } catch (NumberFormatException e) { /* not a number: 0 */ }
        return 0;
    }
    /** Uses {@link Map} only in this Javadoc: a use by convention. */
    protected boolean accept(Class<?> clazz) { return true; }
    private int privateUnused(int x, int unused) {          // FIND:leftover
        return x;
    }
    /** Don't strip this apostrophe as a string start: {@link Arrays} is a use. */
    void javadocApostrophe() { }
    void suppressed() {
        @SuppressWarnings("unused")
        final Integer i = compute();
    }
    void multiLineStrings() {
        assertBoth("abc____", "____",
            5, 10);
    }
    boolean charEquality(char ch0) {
        return ch0 == 'y' || ch0 == 'Y' || ch0 == '1';
    }
    boolean commentedEquality(String a) {
        return a.isEmpty(); // a == "x" in a comment is not a bug
    }
    boolean stringEquality(String a) {
        if (a == "admin") { return true; }                   // FIND:bug
        if ("admin".equals(a)) { return true; }
        return a == null;
    }
}
'''
