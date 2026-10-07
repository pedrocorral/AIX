"""ABAP as the fifth language of `aix code style` (benchmark section 22, abaplint as the reference). Units are
METHOD/FORM/FUNCTION/MODULE up to their END word; a chained statement counts per item; comments and strings do not
count; cyclomatic is McCabe (each WHEN but OTHERS, each AND/OR, CHECK, CATCH, a SELECT that ENDSELECT closes);
cognitive follows Campbell (TRY is not a level, CATCH costs 1 plus the nesting outside); parameters come from the
definition (IMPORTING/EXPORTING/CHANGING, not RETURNING; USING/CHANGING/TABLES of a FORM; the `*"` block of a
function module); a `.testclasses.abap` file is a test. Graph, dead code and clones: test_abapdeps.py."""
import sys, unittest
from pathlib import Path

from helpers import KIT, install, project_cmd, temp_home

sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import abapstyle  # noqa: E402

CLASS = '''CLASS zcl_demo DEFINITION PUBLIC.
  PUBLIC SECTION.
    "! Counts the rows that match.
    METHODS count_rows IMPORTING iv_a TYPE i iv_b TYPE string OPTIONAL
                       EXPORTING ev_c TYPE i
                       RETURNING VALUE(rv_n) TYPE i.
    METHODS: chained_a IMPORTING iv_x TYPE i, chained_b IMPORTING iv_y TYPE i iv_z TYPE i.
  PRIVATE SECTION.
    METHODS helper IMPORTING iv_v TYPE i.
    METHODS expressions IMPORTING iv_x TYPE i iv_y TYPE i.
ENDCLASS.

CLASS zcl_demo IMPLEMENTATION.
  METHOD count_rows.
    DATA: lv_i TYPE i,
          lv_j TYPE i.
    IF iv_a > 0 AND iv_b IS NOT INITIAL OR iv_a = 7.
      LOOP AT mt_rows INTO DATA(ls_row) WHERE id = iv_a.
        CASE ls_row-kind.
          WHEN 'A'.
            lv_i = lv_i + 1.
          WHEN 'B' OR 'C'.
            lv_j = 42.
          WHEN OTHERS.
            CHECK lv_i > 3.
        ENDCASE.
      ENDLOOP.
    ELSEIF iv_a < 0.
      rv_n = -1.
    ELSE.
      rv_n = 0. " a comment with IF inside. and a period.
    ENDIF.
    TRY.
        helper( iv_v = lv_i ).
      CATCH cx_root.
        rv_n = 99.
    ENDTRY.
    SELECT * FROM ztab INTO @DATA(ls_one) WHERE id = @iv_a.
      lv_j = lv_j + 1.
    ENDSELECT.
    SELECT SINGLE id FROM ztab INTO @lv_i WHERE id = @iv_a.
    rv_n = 'IF. LOOP. ENDIF.'.
  ENDMETHOD.

  METHOD chained_a.
    rv = iv_x.
  ENDMETHOD.

  METHOD chained_b.
  ENDMETHOD.

  METHOD helper.
    DATA v TYPE i.
    DATA lv_offset TYPE string.
    lv_offset = iv_v+1(2).
    v = 3.
  ENDMETHOD.

  METHOD expressions.
    DATA(a) = COND #( WHEN iv_x = 1 THEN 'one' WHEN iv_x = 2 THEN 'two' ELSE 'many' ).
    IF iv_x > 0.
      DATA(b) = COND string( WHEN iv_x > 5 AND iv_x < 9 THEN 'mid' ).
    ENDIF.
    DATA(c) = SWITCH #( iv_x WHEN 1 THEN 'a' WHEN 2 THEN 'b' WHEN 3 THEN 'c' ).
    DATA(d) = COND #( WHEN iv_x = 1 THEN COND #( WHEN iv_y = 1 THEN 'x' ELSE 'y' ) ).
  ENDMETHOD.
ENDCLASS.
'''

REPORT = '''REPORT zdemo.

* a classic report
FORM calc USING p_a p_b TYPE i CHANGING p_c TABLES t_rows.
  DO 3 TIMES.
    p_c = p_c + p_a.
  ENDDO.
ENDFORM.

FUNCTION z_demo_fm.
*"----------------------------------------------------------------------
*"*"Local Interface:
*"  IMPORTING
*"     VALUE(IV_X) TYPE  STRING
*"     REFERENCE(IV_Y) TYPE  I
*"  EXPORTING
*"     REFERENCE(EV_Z) TYPE  STRING
*"  TABLES
*"      T_ROWS STRUCTURE  ZROW
*"----------------------------------------------------------------------
  WHILE iv_y > 0.
    AT NEW x.
    ENDAT.
  ENDWHILE.
ENDFUNCTION.

MODULE user_command INPUT.
  CASE sy-ucomm.
    WHEN 'BACK'.
      LEAVE PROGRAM.
  ENDCASE.
ENDMODULE.
'''


def by_name(fxs: list) -> dict:
    return {fx["name"]: fx for fx in fxs}


class AbapUnits(unittest.TestCase):
    def analyse(self, name: str, text: str) -> dict:
        return by_name(abapstyle.functions(Path("src") / name, text, {0, 1, 2, -1, 10, 100, 1000}))

    def test_statements_split_chains_and_ignore_comments_and_strings(self):
        stmts = abapstyle.statements(["DATA: a TYPE i,", "      b TYPE i.", "* IF comment.", 'x = \'IF. a.\'. " IF trailing.', "IF a = 1. b = 2. ENDIF."])
        self.assertEqual([(w, l) for w, _t, l in stmts], [("DATA", 1), ("DATA", 2), ("X", 4), ("IF", 5), ("B", 5), ("ENDIF", 5)])
        self.assertEqual(stmts[0][1], "DATA a TYPE i"); self.assertEqual(stmts[1][1], "DATA b TYPE i")
        chained_call = abapstyle.statements(["lo->set( : name = 'a' ),", "           name = 'b' ).", "DATA: c, d."])
        self.assertEqual([w for w, _t, _l in chained_call], ["LO->SET(", "LO->SET(", "DATA", "DATA"], "a chain inside a call closes the head's parenthesis per item")
        template = abapstyle.statements(["lv = |Branch { get_name(", "    rs-name ) } |.", "MESSAGE lv TYPE 'S'."])
        self.assertEqual([(w, l) for w, _t, l in template], [("LV", 1), ("MESSAGE", 3)], "a template may span lines inside its braces")
        self.assertIn("get_name(", template[0][1], "the code inside a template's braces stays: a call, a condition")
        two_lines = abapstyle.statements(["x = |{ find_params(", "    ls_op ) }{ other( ) }|."])
        self.assertEqual(len(two_lines), 1); self.assertIn("find_params(", two_lines[0][1]); self.assertIn("other(", two_lines[0][1])
        embedded = abapstyle.statements(["x = |a. b { cond #( when v = 'x' then '1' else '2' ) } c|."])
        self.assertEqual(len(embedded), 1); self.assertIn("cond #(", embedded[0][1].lower()); self.assertNotIn("x' then", embedded[0][1])

    def test_class_methods_metrics(self):
        fx = self.analyse("zcl_demo.clas.abap", CLASS)
        m = fx["count_rows"]
        self.assertEqual((m["line"], m["lines"]), (14, 30))
        # 1 + IF + AND + OR + LOOP + WHEN A + WHEN B + its OR (two labels) + CHECK + ELSEIF + CATCH + SELECT loop = 12; WHEN OTHERS, SELECT SINGLE, the comment and the string count nothing
        self.assertEqual(m["cyclomatic"], 12, m["cognitive_items"])
        # IF 1 + runs AND,OR 2 + LOOP (nesting 1) 2 + CASE (nesting 2) 3 + CHECK (nesting 3) 4 + ELSEIF 1 + ELSE 1 + CATCH 1 + SELECT loop 1 = 16; the OR of a WHEN is not a condition
        self.assertEqual(m["cognitive"], 16, m["cognitive_items"])
        self.assertEqual(m["nesting"], 3)
        self.assertEqual(m["params"], 3, "iv_a, iv_b, ev_c; RETURNING is the result")
        self.assertTrue(m["public"]); self.assertTrue(m["docstring"], "abapdoc above the definition")
        self.assertEqual(m["magic"], [(17, 7.0), (23, 42.0), (25, 3.0), (36, 99.0)])
        self.assertEqual((fx["chained_a"]["params"], fx["chained_b"]["params"]), (1, 2), "a chained METHODS: definition")
        self.assertFalse(fx["helper"]["public"]); self.assertEqual(fx["helper"]["params"], 1)
        self.assertEqual(fx["helper"]["short_names"], [(53, "v")])
        self.assertEqual(fx["helper"]["magic"], [(56, 3.0)], "an offset/length `+1(2)` is not a magic number")
        self.assertEqual(fx["chained_b"]["lines"], 2)
        e = fx["expressions"]
        # a: COND, 2 WHENs + ELSE at nesting 0 = 1 + 1 + 1 = 3; b: COND inside an IF (nesting 1), 1 WHEN = 2, its AND = 1, the IF itself = 1;
        # c: SWITCH, 3 WHENs = 1; d: outer COND 1 WHEN = 1, inner COND one level deeper, 1 WHEN + ELSE = 1 + 1 + 1 = 3  -> 3 + 2 + 1 + 1 + 1 + 1 + 3 = 12
        self.assertEqual(e["cognitive"], 12, e["cognitive_items"])
        # cyclomatic: 1 + 2 + 1 (IF) + 1 (WHEN) + 1 (AND) + 3 + 1 + 1 = 11
        self.assertEqual(e["cyclomatic"], 11, e["cognitive_items"])

    def test_classic_units(self):
        fx = self.analyse("zdemo.prog.abap", REPORT)
        self.assertEqual(set(fx), {"calc", "z_demo_fm", "user_command"})
        self.assertEqual(fx["calc"]["params"], 4, "p_a p_b p_c t_rows")
        self.assertEqual(fx["calc"]["cyclomatic"], 2); self.assertTrue(fx["calc"]["docstring"])
        self.assertEqual(fx["z_demo_fm"]["params"], 4, "iv_x iv_y ev_z t_rows from the `*\\\"` block")
        self.assertEqual(fx["z_demo_fm"]["cyclomatic"], 3, "WHILE and AT NEW"); self.assertEqual(fx["z_demo_fm"]["nesting"], 2)
        self.assertEqual(fx["user_command"]["cyclomatic"], 2); self.assertEqual(fx["user_command"]["params"], 0)

    def test_local_class_methods_carry_the_class_name(self):
        text = "CLASS lcl_a IMPLEMENTATION.\n  METHOD run.\n  ENDMETHOD.\nENDCLASS.\nCLASS lcl_b IMPLEMENTATION.\n  METHOD run.\n  ENDMETHOD.\nENDCLASS.\n"
        self.assertEqual(set(self.analyse("zcl_x.clas.locals_imp.abap", text)), {"lcl_a.run", "lcl_b.run"})


class AbapThroughTheTool(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        (self.project / "src").mkdir(parents=True)
        install(self.home, self.project)

    def test_style_table_card_and_tests(self):
        (self.project / "src/zcl_demo.clas.abap").write_text(CLASS)
        (self.project / "src/zcl_demo.clas.testclasses.abap").write_text("CLASS ltcl DEFINITION FOR TESTING.\nENDCLASS.\nCLASS ltcl IMPLEMENTATION.\n  METHOD test_it.\n    IF 1 = 1.\n    ENDIF.\n  ENDMETHOD.\nENDCLASS.\n")
        out = project_cmd(self.project, self.home, "code", "style", "src", check=False).stdout
        self.assertIn("functions analysed 6", out, out)
        self.assertIn("src/zcl_demo.clas.abap:count_rows", out, out)
        card = project_cmd(self.project, self.home, "code", "style", "src/zcl_demo.clas.abap:count_rows", check=False).stdout
        self.assertIn("(line 14, abap)", card, card)
        self.assertIn("cyclomatic complexity    12   limit 10    OVER", card, card)
        self.assertIn("parameters                3   limit 5     ok", card, card)
        gate = project_cmd(self.project, self.home, "code", "style", "src", "--gate", check=False)
        self.assertIn("GATE FAILED", gate.stdout + gate.stderr)
        self.assertIn("test: doubled", project_cmd(self.project, self.home, "code", "style", "src/zcl_demo.clas.testclasses.abap:test_it", check=False).stdout)

    def test_the_other_tools_read_abap_without_a_traceback(self):
        (self.project / "src/zcl_demo.clas.abap").write_text(CLASS)
        (self.project / "src/app.py").write_text("def f(a):\n    return a\n")
        for tool in (["code", "graph"], ["code", "dead"], ["code", "clones"], ["code", "security"], ["code", "stats"]):
            r = project_cmd(self.project, self.home, *tool, "src", check=False)
            self.assertNotIn("Traceback", r.stderr, tool)
        self.assertIn("nodes 2, edges 0", project_cmd(self.project, self.home, "code", "graph", "src", check=False).stdout, "the class and the script are nodes (test_abapdeps.py covers the edges)")

if __name__ == "__main__":
    unittest.main()
