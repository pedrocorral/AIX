# Examples
- pytest + hypothesis: `@given(st.decimals(min_value=0))` for money invariants.
- vitest + fast-check: `fc.assert(fc.property(fc.array(fc.integer()), ...))` for ordering rules.
