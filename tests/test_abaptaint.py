"""The ABAP taint walk (step 3b of the fifth language, benchmark section 26): a PARAMETERS field reaching dynamic SQL
through two method calls across files, stopped by a sanitiser or an allowlist; sy-ucomm reaching SUBMIT (lv); a
remote-enabled function module's parameter reaching CALL 'SYSTEM' while a local module's does not; a request field
written into HTML without escape( ) and not with it; a configuration literal that reaches nothing."""
import unittest

from helpers import install, project_cmd, temp_home

FILES = {
    "src/zprog_in.prog.abap": (
        "REPORT zprog_in.\nPARAMETERS p_tab TYPE string.\nPARAMETERS p_prog TYPE string.\n"
        "START-OF-SELECTION.\n  PERFORM run USING p_tab.\n  PERFORM pick.\n"
        "FORM run USING pv_tab TYPE string.\n  DATA lv_name TYPE string.\n  lv_name = pv_tab.\n  NEW zcl_reader( )->read( iv_table = lv_name ).\n"
        "  NEW zcl_reader( )->read_checked( iv_table = lv_name ).\n  NEW zcl_reader( )->read_listed( iv_table = lv_name ).\n"
        "  DATA lv_fixed TYPE string.\n  lv_fixed = 'ZCONFIG'.\n  NEW zcl_reader( )->read( iv_table = lv_fixed ).\nENDFORM.\n"
        "FORM pick.\n  DATA lv_prog TYPE string.\n  lv_prog = sy-ucomm.\n  SUBMIT (lv_prog) AND RETURN.\nENDFORM.\n"),
    "src/zcl_reader.clas.abap": (
        "CLASS zcl_reader DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    METHODS read IMPORTING iv_table TYPE string.\n    METHODS read_checked IMPORTING iv_table TYPE string.\n"
        "    METHODS read_listed IMPORTING iv_table TYPE string.\n  PRIVATE SECTION.\n    METHODS fetch IMPORTING iv_name TYPE string.\nENDCLASS.\n"
        "CLASS zcl_reader IMPLEMENTATION.\n  METHOD read.\n    DATA lv TYPE string.\n    lv = |{ iv_table }|.\n    fetch( iv_name = lv ).\n  ENDMETHOD.\n"
        "  METHOD read_checked.\n    DATA(lv) = cl_abap_dyn_prg=>check_table_name_str( val = iv_table packages = '' ).\n    fetch( iv_name = lv ).\n  ENDMETHOD.\n"
        "  METHOD read_listed.\n    CASE iv_table.\n      WHEN 'ZA' OR 'ZB'.\n        fetch( iv_name = iv_table ).\n    ENDCASE.\n  ENDMETHOD.\n"
        "  METHOD fetch.\n    DATA lt TYPE STANDARD TABLE OF string.\n    SELECT * FROM (iv_name) INTO TABLE lt.\n  ENDMETHOD.\nENDCLASS.\n"),
    "src/zfg_rfc.fugr.z_remote_run.abap": "FUNCTION z_remote_run.\n*\"  IMPORTING\n*\"     VALUE(IV_CMD) TYPE  STRING\n  CALL 'SYSTEM' ID 'COMMAND' FIELD iv_cmd.\nENDFUNCTION.\n",
    "src/zfg_rfc.fugr.z_local_run.abap": "FUNCTION z_local_run.\n*\"  IMPORTING\n*\"     VALUE(IV_CMD) TYPE  STRING\n  CALL 'SYSTEM' ID 'COMMAND' FIELD iv_cmd.\nENDFUNCTION.\n",
    "src/zfg_rfc.fugr.xml": "<?xml version=\"1.0\"?>\n<abapGit>\n <FUNCTIONS>\n  <item>\n   <FUNCNAME>Z_REMOTE_RUN</FUNCNAME>\n   <REMOTE_CALL>R</REMOTE_CALL>\n  </item>\n  <item>\n   <FUNCNAME>Z_LOCAL_RUN</FUNCNAME>\n  </item>\n </FUNCTIONS>\n</abapGit>\n",
    "src/zcl_page.clas.abap": (
        "CLASS zcl_page DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    METHODS render IMPORTING ii_event TYPE REF TO zif_event ri_html TYPE REF TO zif_html.\nENDCLASS.\n"
        "CLASS zcl_page IMPLEMENTATION.\n  METHOD render.\n    DATA(lv_name) = ii_event->form_data( )->get( 'name' ).\n"
        "    ri_html->add( |<td>{ lv_name }</td>| ).\n    ri_html->add( |<td>{ escape( val = lv_name format = cl_abap_format=>e_html_text ) }</td>| ).\n"
        "    DATA lv_html TYPE string.\n    lv_html = |<b>{ lv_name }</b>|.\n    ri_html->add( lv_html ).\n  ENDMETHOD.\nENDCLASS.\n"),
}


class AbapTaint(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        for rel, text in FILES.items():
            (self.project / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.project / rel).write_text(text, encoding="utf-8")
        install(self.home, self.project)
        self.out = project_cmd(self.project, self.home, "code", "vulnerabilities", "--taint", "src", check=False).stdout

    def test_parameter_reaches_dynamic_sql_two_calls_away_unless_checked(self):
        out = self.out
        self.assertIn("taint paths (Python, JS/TS, Java, ABAP)", out, out)
        self.assertRegex(out, r"zcl_reader\.clas\.abap:27  input reaches dynamic SQL", "p_tab -> run -> read -> fetch\n" + out)
        self.assertIn("p_tab: PARAMETERS (line 2) via zprog_in (line 5) via run (line 10) via read (line 13)", out, out)
        self.assertEqual(out.count("input reaches dynamic SQL"), 1, "one SQL path: the checked, the listed and the literal ones end before fetch\n" + out)

    def test_sy_ucomm_reaches_submit(self):
        self.assertRegex(self.out, r"zprog_in\.prog\.abap:20  input reaches program chosen at run time", self.out)

    def test_remote_function_module_parameter_is_input_local_is_not(self):
        self.assertRegex(self.out, r"z_remote_run\.abap:4  input reaches OS command", self.out)
        self.assertNotRegex(self.out, r"z_local_run\.abap:4", "a local function module's parameter is not input\n" + self.out)

    def test_request_field_into_html_without_escape(self):
        out = self.out
        self.assertRegex(out, r"zcl_page\.clas\.abap:8  input reaches HTML output", out)
        self.assertNotRegex(out, r"zcl_page\.clas\.abap:9\b", "escaped\n" + out)
        self.assertRegex(out, r"zcl_page\.clas\.abap:12  input reaches HTML output", "through a string variable\n" + out)
        self.assertIn("request field read in render", out, out)


if __name__ == "__main__":
    unittest.main()
