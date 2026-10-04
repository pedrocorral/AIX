"""Rust cognitive complexity by SonarSource's definition, checked against rust-code-analysis on ripgrep and bat
(benchmark section 16): `?` is not a ternary, a match arm's block is not a level of its own, a match guard is part of
its arm; `match`, `if let`, `while let` and `loop` are branches."""
import sys, tempfile, unittest
from pathlib import Path

from helpers import KIT

sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import stylemetrics  # noqa: E402

SAMPLE = '''
fn propagates(p: &str) -> Result<u8, E> {
    let a = read(p)?;
    let b = parse(a)?;
    Ok(b)
}

fn arms(arg: Arg) -> u8 {
    match arg {
        Arg::Short(ch) if ch == 'h' => {
            if ch.is_ascii() { 1 } else { 2 }
        }
        Arg::Long(name) => {
            if name.is_empty() { 3 } else { 4 }
        }
        _ => 0,
    }
}

fn loops(items: &[u8]) -> u8 {
    let mut n = 0;
    loop {
        if let Some(x) = items.get(n) {
            n += *x as usize;
        } else {
            break;
        }
    }
    while let Some(y) = next() {
        n += y;
    }
    n as u8
}
'''
WANT = dict(propagates=0, arms=7, loops=5)   # match 1, then per arm an if at the match level (2) and its else (1); loop 1 + if let 2 + else 1 + while let 1


class Cognitive(unittest.TestCase):
    def test_every_shape(self):
        d = Path(tempfile.mkdtemp()); f = d / "s.rs"; f.write_text(SAMPLE)
        got = {fx["name"]: fx["cognitive"] for fx in stylemetrics.functions_in(f)}
        self.assertEqual(got, WANT)


if __name__ == "__main__":
    unittest.main()
