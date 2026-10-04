"""Python cognitive complexity by SonarSource's definition, checked against complexipy on four projects (benchmark
section 16): a comprehension is a loop (+1 and its nesting level, +1 per further `for`, +1 per `if` clause), an
`else:` holding an `if` is an else plus a nested if (4), an `elif` is one branch (2), a ternary inside an f-string
or a lambda counts, a nested function adds a nesting level."""
import ast, sys, unittest

from helpers import KIT

sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import stylemetrics  # noqa: E402

SAMPLE = '''
def comprehension(xs):
    return [x for x in xs]

def comprehension_if(xs):
    return [x for x in xs if x]

def comprehension_in_for(xss):
    for xs in xss:
        print([x for x in xs if x])

def two_fors(xss):
    return [x for xs in xss for x in xs]

def generator_in_call(xs):
    return sum(x > 1 for x in xs)

def dict_comprehension(d):
    return {k: v for k, v in d.items() if v}

def else_if(a, b):
    if a:
        pass
    else:
        if b:
            pass

def elif_chain(a, b):
    if a:
        pass
    elif b:
        pass

def ternary_in_fstring(a):
    return f"{'x' if a else 'y'}"

def lambda_with_ternary(xs):
    return sorted(xs, key=lambda x: 1 if x else 0)

def nested_function(xs):
    def inner(x):
        if x:
            return 1
    return inner
'''
WANT = dict(comprehension=1, comprehension_if=2, comprehension_in_for=4, two_fors=2, generator_in_call=1, dict_comprehension=2,
            else_if=4, elif_chain=2, ternary_in_fstring=1, lambda_with_ternary=2, nested_function=2)


class Cognitive(unittest.TestCase):
    def test_every_shape(self):
        got = {fn.name: stylemetrics.cognitive_py(fn)[0] for fn in ast.parse(SAMPLE).body}
        self.assertEqual(got, WANT)


if __name__ == "__main__":
    unittest.main()
