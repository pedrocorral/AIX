The refactor skills (aix skills refactor)

One skill per `aix code` finding type; each says how to fix it safely, how to verify (re-run the tool, run the
tests) and what to write in the hand-off. One finding per change.
  refactor-cycle        CYCLE / UPWARD: extract the shared part into a leaf, or invert through a port
  refactor-shortcut     SHORTCUT: use the intermediate's result, move the type to a stable module, or split
  refactor-hub          HUB (not a root): split by stability, the stable part becomes a leaf
  refactor-dead         DEAD MODULE / FUNCTION: prove unreachable (grep strings, frameworks), delete, test
  refactor-clone        EXACT / NEAR: extract the identical part as a leaf, parametrise the difference
  refactor-readability  OVER metric: nesting, cognitive, cyclomatic, lines, parameters, one metric per change
  refactor-modernise    modernise line: one construct per change, no behaviour change
Every report names the skill on its last line; review-code-review proposes it; core-sdd-workflow runs it.
