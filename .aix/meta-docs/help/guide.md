aix guide [CHAPTER...] [--all]

The user guide: 1 start, 2 concepts, 3 install, 4 agents, 5 skills, 6 instructions, 7 organisation, 8 docs,
9 code, 10 maintain, 11 reference. `aix guide` lists them; `aix guide skills` or `aix guide 5` prints one; `--all`
prints everything. Long output goes through your pager ($PAGER, else less) in a terminal. The chapters live in
.aix/meta-docs/guide/ and travel with every project; an organisation or a project can replace a chapter by placing
the same file under its layer's meta-docs/guide/.
