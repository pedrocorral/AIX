"""The token walker of the brace languages: nesting depth, cyclomatic and cognitive complexity from a cleaned body."""
import re

TOKEN_RX = re.compile(r"\{|\}|;|=>|\b(if|for|while|switch|catch|match|loop|else|try|finally|synchronized)\b|&&|\|\||\?\?|\?(?![.?:])")   # `?.` and `x?: T` are not branches
BRANCH_WORDS = ("if", "for", "while", "switch", "catch", "match", "loop")
FLAT_BLOCKS = ("try", "finally", "synchronized")   # their brace is not a nesting level (Campbell 2017: catch is, try is not)
OPERATORS = ("&&", "||", "??")


class _TokenWalk:
    """Brace-language metrics from a cleaned body: nesting depth (every block), cyclomatic (McCabe: each branch and
    boolean operator) and cognitive complexity (Campbell 2017: +1 per branch plus the nesting level of if/else/loop/
    catch/lambda blocks, +1 per sequence of like boolean operators, `else if` is one branch)."""
    def __init__(self, start_line: int, lang: str = "js"):
        self.lang, self.start_line, self.depth, self.cur = lang, start_line, 0, 0
        self.cog, self.cyc, self.items, self.deepest_line = 0, 1, [], start_line
        self.nest, self.stack, self.flat, self.run, self.after_else = 0, [], True, None, False   # the body's own brace is not a level

    def feed(self, tok: str, line: int):
        after_else, self.after_else = self.after_else, False
        if tok == "?" and self.lang == "rust":
            return   # Rust's `?` propagates an error, it is not a ternary (benchmark section 16)
        if tok == "=>":
            self.flat = self.lang == "rust"   # a `match` arm's block is not a level of its own: the `match` is the level
            return
        if tok == "{":
            self._open(line)
        elif tok == "}":
            self.cur -= 1; self.nest -= self.stack.pop() if self.stack else 0
        elif tok in FLAT_BLOCKS or tok == ";":
            self.flat, self.run = tok != ";", None
        elif tok in BRANCH_WORDS:
            self._branch(tok, line, after_else)
        else:
            self._operator(tok, line)

    def _operator(self, tok: str, line: int):
        """`&&`, `||`, `??`, `?` and `else`: cyclomatic counts each operator, cognitive one per run of like operators."""
        self.cyc += tok != "else"; self.after_else = tok == "else"
        if tok in OPERATORS and tok == self.run:
            return
        self.run = tok if tok in OPERATORS else None
        self.cog += 1
        self.items.append((line, 1, {"else": "else (+1)", "?": "ternary (+1)"}.get(tok, "boolean operator (+1)")))

    def _open(self, line: int):
        self.cur += 1; self.stack.append(not self.flat); self.nest += not self.flat; self.flat = False
        if self.cur > self.depth:
            self.depth, self.deepest_line = self.cur, line

    def _branch(self, tok: str, line: int, after_else: bool):
        self.cyc += 1; self.run = None
        if tok == "if" and after_else:
            self.items.append((line, 0, "else if (counted with else)")); return
        inc = 1 + self.nest; self.cog += inc
        self.items.append((line, inc, f"{tok} (+1, nesting +{self.nest})" if self.nest else f"{tok} (+1)"))
