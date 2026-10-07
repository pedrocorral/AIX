"""ABAP in `aix code graph`, `aix code dead` and `aix code clones` (step 2 of the fifth language, benchmark section 23).
A node is one abapGit object: a class with its locals folded in, an interface, a program, an include, a function group
with its function-module files folded in; a `.testclasses.abap` file is a test node of its own. An edge is one file
naming another object: `zcl_x=>`, `TYPE REF TO`, `NEW zcl_x(`, `CREATE OBJECT ... TYPE`, `INHERITING FROM`,
`INTERFACES`, `TYPE zif_x=>ty`, `RAISE EXCEPTION TYPE`, `CATCH`, `CALL FUNCTION 'Z_X'`, `INCLUDE`, `SUBMIT`. SAP
standard names (`cl_*`, `if_*`) and dictionary types resolve to nothing and are not edges. Entry points: a program
(REPORT/PROGRAM), a function group, a class implementing `if_oo_adt_classrun`, a test class."""
import unittest

from helpers import install, project_cmd, temp_home

FILES = {
    "src/zif_api.intf.abap": "INTERFACE zif_api PUBLIC.\n  TYPES ty_row TYPE string.\n  METHODS run.\nENDINTERFACE.\n",
    "src/zcl_core.clas.abap": "CLASS zcl_core DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    INTERFACES zif_api.\n    DATA mv_row TYPE zif_api=>ty_row.\n    DATA mo_desc TYPE REF TO cl_abap_typedescr.\n"
                             "    METHODS fail RAISING zcx_error.\nENDCLASS.\nCLASS zcl_core IMPLEMENTATION.\n  METHOD zif_api~run.\n    TRY.\n        fail( ).\n      CATCH zcx_error.\n    ENDTRY.\n  ENDMETHOD.\n"
                             "  METHOD fail.\n    RAISE EXCEPTION TYPE zcx_error.\n  ENDMETHOD.\nENDCLASS.\n",
    "src/zcl_core.clas.locals_imp.abap": "CLASS lcl_helper IMPLEMENTATION.\n  METHOD go.\n    zcl_util=>helper( 1 ).\n  ENDMETHOD.\nENDCLASS.\n",
    "src/zcl_core.clas.testclasses.abap": "CLASS ltcl_core DEFINITION FOR TESTING.\nENDCLASS.\nCLASS ltcl_core IMPLEMENTATION.\n  METHOD test_run.\n    DATA lo TYPE REF TO zcl_core.\n    DATA lo_orphan TYPE REF TO zcl_orphan.\n  ENDMETHOD.\nENDCLASS.\n",
    "src/zcl_util.clas.abap": "CLASS zcl_util DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    CLASS-METHODS helper IMPORTING iv_n TYPE i.\nENDCLASS.\nCLASS zcl_util IMPLEMENTATION.\n  METHOD helper.\n"
                             "    DATA lv_a TYPE i.\n    DATA lv_b TYPE i.\n    lv_a = iv_n + 1.\n    lv_b = lv_a * 2.\n    IF lv_b > 10.\n      lv_a = 0.\n    ENDIF.\n  ENDMETHOD.\nENDCLASS.\n",
    "src/zcx_error.clas.abap": "CLASS zcx_error DEFINITION PUBLIC INHERITING FROM cx_static_check.\nENDCLASS.\nCLASS zcx_error IMPLEMENTATION.\nENDCLASS.\n",
    "src/zcl_child.clas.abap": "CLASS zcl_child DEFINITION PUBLIC INHERITING FROM zcl_core.\n  PUBLIC SECTION.\n    METHODS other IMPORTING iv_k TYPE i.\n    METHODS make.\nENDCLASS.\nCLASS zcl_child IMPLEMENTATION.\n  METHOD other.\n"
                              "    DATA lv_x TYPE i.\n    DATA lv_y TYPE i.\n    lv_x = iv_k + 5.\n    lv_y = lv_x * 3.\n    IF lv_y > 99.\n      lv_x = 7.\n    ENDIF.\n  ENDMETHOD.\n"
                              "  METHOD make.\n    DATA lo TYPE REF TO object.\n    CREATE OBJECT lo TYPE zcl_util.\n  ENDMETHOD.\nENDCLASS.\n",
    "src/zcl_cycle_a.clas.abap": "CLASS zcl_cycle_a DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    DATA mo_b TYPE REF TO zcl_cycle_b.\nENDCLASS.\nCLASS zcl_cycle_a IMPLEMENTATION.\nENDCLASS.\n",
    "src/zcl_cycle_b.clas.abap": "CLASS zcl_cycle_b DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    DATA mo_a TYPE REF TO zcl_cycle_a.\nENDCLASS.\nCLASS zcl_cycle_b IMPLEMENTATION.\nENDCLASS.\n",
    "src/zcl_runner.clas.abap": "CLASS zcl_runner DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    INTERFACES if_oo_adt_classrun.\nENDCLASS.\nCLASS zcl_runner IMPLEMENTATION.\n  METHOD if_oo_adt_classrun~main.\n    DATA(lo) = NEW zcl_core( ).\n  ENDMETHOD.\nENDCLASS.\n",
    "src/zcl_orphan.clas.abap": "CLASS zcl_orphan DEFINITION PUBLIC.\nENDCLASS.\nCLASS zcl_orphan IMPLEMENTATION.\nENDCLASS.\n",
    "src/zcl_lonely.clas.abap": "CLASS zcl_lonely DEFINITION PUBLIC.\nENDCLASS.\nCLASS zcl_lonely IMPLEMENTATION.\nENDCLASS.\n",
    "src/zprog_main.prog.abap": "REPORT zprog_main.\nINCLUDE zinc_forms.\nDATA go_a TYPE REF TO zcl_cycle_a.\nDATA go_t TYPE REF TO zcl_typed.\nDATA go_f TYPE REF TO zcl_factory.\nDATA go_2 TYPE REF TO zcl_twice.\nSTART-OF-SELECTION.\n  DATA(lo) = NEW zcl_child( ).\n  CALL FUNCTION 'Z_CALC'\n    EXPORTING iv_n = 1.\n  SUBMIT zprog_other AND RETURN.\n",
    "src/zprog_other.prog.abap": "REPORT zprog_other.\nWRITE 'other'.\n",
    "src/zinc_forms.prog.abap": "FORM show.\n  WRITE 'x'.\nENDFORM.\n",
    "src/zfg_calc.fugr.saplzfg_calc.abap": "INCLUDE lzfg_calctop.\nINCLUDE lzfg_calcuxx.\n",
    "src/zfg_calc.fugr.lzfg_calctop.abap": "FUNCTION-POOL zfg_calc.\n",
    "src/zfg_calc.fugr.z_calc.abap": "FUNCTION z_calc.\n*\"  IMPORTING\n*\"     VALUE(IV_N) TYPE  I\n  DATA lv TYPE i.\n  lv = iv_n.\nENDFUNCTION.\n",
    "src/zpool.type.abap": "TYPE-POOL zpool.\nTYPES zpool_ty_row TYPE string.\n",
    "src/zcl_typed.clas.abap": "CLASS zcl_typed DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    DATA mv TYPE zpool_ty_row.\nENDCLASS.\nCLASS zcl_typed IMPLEMENTATION.\nENDCLASS.\n",
    "src/zcl_factory.clas.abap": "CLASS zcl_factory DEFINITION PUBLIC GLOBAL FRIENDS zcl_injector.\n  PUBLIC SECTION.\n    CLASS-METHODS make IMPORTING iv_kind TYPE string.\nENDCLASS.\nCLASS zcl_factory IMPLEMENTATION.\n  METHOD make.\n"
                                 "    DATA lo TYPE REF TO object.\n    CREATE OBJECT lo TYPE (lcl_names=>of( iv_kind )).\n  ENDMETHOD.\nENDCLASS.\n",
    "src/zcl_factory.clas.locals_imp.abap": "CLASS lcl_names IMPLEMENTATION.\n  METHOD of.\n    rv_class = 'ZCL_PLUGIN_' && iv_kind.\n  ENDMETHOD.\nENDCLASS.\n",
    "src/zcl_injector.clas.abap": "CLASS zcl_injector DEFINITION PUBLIC.\nENDCLASS.\nCLASS zcl_injector IMPLEMENTATION.\nENDCLASS.\n",
    "src/zcl_plugin_csv.clas.abap": "CLASS zcl_plugin_csv DEFINITION PUBLIC.\nENDCLASS.\nCLASS zcl_plugin_csv IMPLEMENTATION.\nENDCLASS.\n",
    "src/a/zcl_twice.clas.abap": "CLASS zcl_twice DEFINITION PUBLIC.\nENDCLASS.\nCLASS zcl_twice IMPLEMENTATION.\nENDCLASS.\n",
    "src/b/zcl_twice.clas.abap": "CLASS zcl_twice DEFINITION PUBLIC.\nENDCLASS.\nCLASS zcl_twice IMPLEMENTATION.\nENDCLASS.\n",
}


class AbapGraph(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        for rel, text in FILES.items():
            (self.project / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.project / rel).write_text(text, encoding="utf-8")
        install(self.home, self.project)

    def test_nodes_edges_and_the_cycle(self):
        out = project_cmd(self.project, self.home, "code", "graph", "src", check=False).stdout
        # nodes: zif_api, zcl_core (+locals), its test class, zcl_util, zcx_error, zcl_child, zcl_cycle_a, zcl_cycle_b, zcl_runner, zcl_orphan,
        # zcl_lonely, zprog_main, zprog_other, zinc_forms, zfg_calc (three files), zpool, zcl_typed, zcl_factory (+locals), zcl_injector, zcl_plugin_csv, zcl_twice in two folders = 22
        # edges: core->api, core->util (from the locals), core->cx, child->core, child->util, main->child, main->inc, main->fg, main->other,
        # main->cycle_a, main->typed, main->factory, a->b, b->a, test->core, test->orphan, runner->core, typed->pool (a `zpool_` name) = 18;
        # factory->injector (FRIENDS), main->both zcl_twice (the same name in two folders: both, never one by luck) = 21; cl_abap_typedescr,
        # cx_static_check, if_oo_adt_classrun resolve to nothing; the plugin created by name is no edge
        self.assertIn("nodes 22, edges 21", out, out)
        self.assertIn("cycles 1", out, out); self.assertIn("closes a cycle among 2 nodes: src/zcl_cycle_a.clas.abap, src/zcl_cycle_b.clas.abap", out, out)

    def test_dead_objects(self):
        out = project_cmd(self.project, self.home, "code", "dead", "src", check=False).stdout
        self.assertIn("DEAD MODULES 1", out, out)
        self.assertIn("src/zcl_lonely.clas.abap", out, out)
        self.assertNotIn("    src/zpool.type.abap", out, "the type pool is reached through its zpool_ name\n" + out)
        self.assertNotIn("    src/zcl_plugin_csv", out, "created by name from the 'ZCL_PLUGIN_' prefix built in the factory's locals\n" + out)
        self.assertNotIn("    src/zcl_injector", out, "named as a FRIEND of the factory\n" + out)
        self.assertNotIn("zcl_twice", out, "both files of a name are reached\n" + out)
        for live in ("zcl_orphan", "zinc_forms", "zprog_other", "zfg_calc", "zcl_runner", "zcl_cycle_b"):
            self.assertNotIn(f"    src/{live}", out, f"{live} is reached or is an entry point\n" + out)

    def test_clones_between_methods(self):
        out = project_cmd(self.project, self.home, "code", "clones", "src", check=False).stdout
        self.assertIn("exact clone groups 1", out, out)
        self.assertIn("zcl_util.clas.abap:helper", out, out); self.assertIn("zcl_child.clas.abap:other", out, out)


if __name__ == "__main__":
    unittest.main()
