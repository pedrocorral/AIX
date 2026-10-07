"""ABAP in `aix code security` (step 3 of the fifth language, benchmark section 25): dynamic Open SQL unless the
variable holds a literal of the same unit, EXEC SQL, code generated at run time, an OS command, a program, function
or transaction named at run time, CALL TRANSACTION without an authority check, an AUTHORITY-CHECK whose sy-subrc is
not read, CLIENT SPECIFIED, a file path in a variable, a plain http:// client. Every shape has its safe twin on the
line after it; comments and strings never fire."""
import unittest

from helpers import install, project_cmd, temp_home

SAMPLE = """CLASS zcl_sec DEFINITION PUBLIC.
  PUBLIC SECTION.
    METHODS run IMPORTING iv_table TYPE string iv_where TYPE string iv_prog TYPE string iv_path TYPE string.
ENDCLASS.
CLASS zcl_sec IMPLEMENTATION.
  METHOD run.
    DATA lt_rows TYPE STANDARD TABLE OF string.
    DATA lv_fixed TYPE string.
    SELECT * FROM (iv_table) INTO TABLE lt_rows.
    SELECT * FROM ztab INTO TABLE lt_rows WHERE id = @iv_table.
    SELECT * FROM ztab INTO TABLE lt_rows WHERE (iv_where).
    lv_fixed = 'ZTAB'.
    SELECT * FROM (lv_fixed) INTO TABLE lt_rows.
    INSERT (iv_table) FROM TABLE lt_rows.
    DELETE (zcl_sec=>c_tabname) FROM TABLE lt_rows.
    DELETE TEXTPOOL iv_prog LANGUAGE 'E'.
    EXEC SQL.
      SELECT 1 FROM dual
    ENDEXEC.
    GENERATE SUBROUTINE POOL lt_rows NAME lv_fixed.
    CALL 'SYSTEM' ID 'COMMAND' FIELD iv_path.
    SUBMIT (iv_prog) AND RETURN.
    SUBMIT zfixed_report AND RETURN.
    CALL FUNCTION iv_prog.
    CALL FUNCTION 'Z_FIXED'.
    CALL TRANSACTION iv_prog.
    CALL TRANSACTION 'SE38' WITH AUTHORITY-CHECK.
    SELECT * FROM ztab CLIENT SPECIFIED INTO TABLE lt_rows WHERE mandt = '100'.
    OPEN DATASET iv_path FOR INPUT IN TEXT MODE ENCODING DEFAULT.
    OPEN DATASET '/usr/sap/fixed.txt' FOR INPUT IN TEXT MODE ENCODING DEFAULT.
    cl_http_client=>create_by_url( EXPORTING url = 'http://example.org' IMPORTING client = DATA(lo_plain) ).
    cl_http_client=>create_by_url( EXPORTING url = 'https://example.org' IMPORTING client = DATA(lo_tls) ).
*   SELECT * FROM (iv_table) INTO TABLE lt_rows.
    lv_fixed = 'SELECT * FROM (iv_table)'.   " a string, not a statement
    key1 = ls_dm02l-entidfrom_value.
    api_key = 'abcd1234efgh5678ijkl9012'.
  ENDMETHOD.
ENDCLASS.
"""

AUTHORITY = """REPORT zauth.
FORM checked.
  AUTHORITY-CHECK OBJECT 'S_TCODE' ID 'TCD' FIELD 'SE38'.
  IF sy-subrc <> 0.
    RETURN.
  ENDIF.
  CALL TRANSACTION 'SE38'.
ENDFORM.
FORM unchecked.
  AUTHORITY-CHECK OBJECT 'S_TCODE' ID 'TCD' FIELD 'SE38'.
  CALL TRANSACTION 'SE38'.
ENDFORM.
FORM none.
  CALL TRANSACTION 'SE38'.
ENDFORM.
"""


class AbapSecurity(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        (self.project / "src").mkdir(parents=True)
        (self.project / "src/zcl_sec.clas.abap").write_text(SAMPLE)
        (self.project / "src/zauth.prog.abap").write_text(AUTHORITY)
        install(self.home, self.project)
        self.out = project_cmd(self.project, self.home, "code", "security", "src", check=False).stdout

    def test_every_shape_fires_and_its_safe_twin_does_not(self):
        out = self.out
        for line, title in ((9, "SQL built at run time"), (11, "SQL built at run time"), (14, "INSERT (iv_table)"), (15, "a class constant is dynamic too"), (16, "DELETE TEXTPOOL"),
                            (17, "native SQL"), (20, "code generated"), (21, "OS command"), (22, "chosen at run time"), (24, "chosen at run time"), (26, "chosen at run time"),
                            (28, "cross-client"), (29, "file path held in a variable"), (31, "plain http")):
            self.assertRegex(out, rf"zcl_sec\.clas\.abap:{line}\b", f"line {line}: {title}\n{out}")
        self.assertRegex(out, r"zcl_sec\.clas\.abap:36\b", "a quoted key literal is a secret\n" + out)
        for line in (10, 13, 23, 25, 27, 30, 32, 33, 34, 35):
            self.assertNotRegex(out, rf"zcl_sec\.clas\.abap:{line}\b", f"line {line} is the safe twin, a comment, a string, or a variable assigned to a key field\n{out}")

    def test_authority_checks(self):
        out = self.out
        self.assertNotRegex(out, r"zauth\.prog\.abap:(3|7)\b", "checked: sy-subrc read, transaction after the check\n" + out)
        self.assertRegex(out, r"zauth\.prog\.abap:10\b", "AUTHORITY-CHECK whose result is not read\n" + out)
        self.assertNotRegex(out, r"zauth\.prog\.abap:11\b", "the unit has an AUTHORITY-CHECK\n" + out)
        self.assertRegex(out, r"zauth\.prog\.abap:14\b", "CALL TRANSACTION with no check at all\n" + out)
        self.assertIn("CWE-862", out); self.assertIn("CWE-285", out)


if __name__ == "__main__":
    unittest.main()
