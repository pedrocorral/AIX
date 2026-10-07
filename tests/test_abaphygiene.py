"""ABAP hygiene in `aix code style` (benchmark section 27): a swallowed CATCH unless a comment says why, a variable
declared and never named again, abaplint's definition (components of a structure are not variables, an inline
declaration nothing names later is a leftover), an IMPORTING parameter of a private method
never named (public, interface and redefined methods keep theirs), a pass-through method forwarding every parameter
to one call (an interface implementation or one that adds a value is not)."""
import unittest

from helpers import install, project_cmd, temp_home

CLASS = """CLASS zcl_hyg DEFINITION PUBLIC.
  PUBLIC SECTION.
    INTERFACES zif_api.
    METHODS catches.
    METHODS variables IMPORTING iv_in TYPE i.
    METHODS api IMPORTING iv_unused TYPE i.
    METHODS wrap IMPORTING iv_a TYPE i iv_b TYPE i.
    METHODS adds IMPORTING iv_a TYPE i.
  PRIVATE SECTION.
    METHODS helper IMPORTING iv_used TYPE i iv_never TYPE i.
    DATA mo_x TYPE REF TO zcl_other.
ENDCLASS.
CLASS zcl_hyg IMPLEMENTATION.
  METHOD catches.
    TRY.
        helper( iv_used = 1 iv_never = 2 ).
      CATCH cx_root.
    ENDTRY.
    TRY.
        helper( iv_used = 1 iv_never = 2 ).
      CATCH cx_root.
        " nothing to do: the default is fine
    ENDTRY.
    TRY.
        helper( iv_used = 1 iv_never = 2 ).
      CATCH cx_root INTO DATA(lx).
        WRITE lx->get_text( ).
    ENDTRY.
  ENDMETHOD.
  METHOD variables.
    DATA lv_unused TYPE i.
    DATA lv_written TYPE i.
    DATA lv_read TYPE i.
    DATA: BEGIN OF ls_row,
            a TYPE i,
          END OF ls_row.
    CONSTANTS lc_max TYPE i VALUE 10.
    FIELD-SYMBOLS <fs> TYPE any.
    lv_written = 1.
    lv_read = iv_in.
    WRITE lv_read.
    ls_row-a = 1.
    WRITE ls_row-a.
    WRITE lc_max.
    ASSIGN lv_read TO <fs>.
    WRITE <fs>.
    DATA(lv_inline) = 5.
    mo_x->get( IMPORTING ev_out = DATA(lv_target) ).
    DATA lv_tmpl TYPE string.
    lv_tmpl = |{ lv_read }|.
    WRITE lv_tmpl.
  ENDMETHOD.
  METHOD api.
  ENDMETHOD.
  METHOD wrap.
    mo_x->do( iv_a = iv_a iv_b = iv_b ).
  ENDMETHOD.
  METHOD adds.
    mo_x->do( iv_a = iv_a iv_b = 7 ).
  ENDMETHOD.
  METHOD helper.
    WRITE iv_used.
  ENDMETHOD.
  METHOD zif_api~run.
    mo_x->do( iv_a = iv_a ).
  ENDMETHOD.
ENDCLASS.
"""


class AbapHygiene(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        (self.project / "src").mkdir(parents=True)
        (self.project / "src/zcl_hyg.clas.abap").write_text(CLASS)
        install(self.home, self.project)

    def card(self, method: str) -> str:
        return project_cmd(self.project, self.home, "code", "style", f"src/zcl_hyg.clas.abap:{method}", check=False).stdout

    def test_swallowed_catch_unless_a_comment_says_why(self):
        card = self.card("catches")
        self.assertIn("line 17    swallowed: this CATCH does nothing and says nothing", card, card)
        self.assertEqual(card.count("swallowed"), 1, "the commented and the handling CATCH are not findings\n" + card)

    def test_variables_declared_and_never_used(self):
        card = self.card("variables")
        for name in ("lv_unused", "lv_inline", "lv_target"):
            self.assertIn(f"leftover: variable `{name}` in `variables` is declared and never used", card, card)
        for name in ("lv_written", "lv_read", "ls_row", "lc_max", "<fs>", "fs", "lv_tmpl", "iv_in"):
            self.assertNotIn(f"variable `{name}`", card, f"{name} is named again (abaplint's definition: a write is a use)\n" + card)
        self.assertEqual(card.count("leftover"), 3, card)

    def test_unused_private_parameter_only(self):
        self.assertIn("leftover: parameter `iv_never` of `helper` is never read", self.card("helper"))
        self.assertNotIn("leftover", self.card("api"), "a public method keeps its parameters by contract")
        self.assertNotIn("leftover", self.card("zif_api~run"), "an interface implementation keeps its parameters")

    def test_pass_through_method(self):
        self.assertIn("pass-through            yes", self.card("wrap"))
        self.assertIn("pass-through             no", self.card("adds"))
        self.assertIn("pass-through             no", self.card("zif_api~run"))
        table = project_cmd(self.project, self.home, "code", "style", "src", check=False).stdout
        self.assertIn("pass-through 1, leftovers 4, swallowed 1", table, table)


if __name__ == "__main__":
    unittest.main()
