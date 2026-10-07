"""ABAP in `aix code graph --functions` and `aix code dead --functions` (step 2b of the fifth language, benchmark
section 24). Call edges are resolved only through a known target: `me->m(` and a bare `m(` in the class, `super->m(`,
`zcl_x=>m(`, a receiver declared TYPE REF TO a project class (in the unit, the parameters or the attributes), `NEW
zcl_x( )`, a factory's RETURNING type, a receiver typed with a project interface (every implementation), `PERFORM`,
`CALL FUNCTION 'Z'`, `CALL METHOD` in the same shapes; an unknown receiver is unresolved, never guessed by name. Dead
methods: private or protected, never named by any call anywhere (tests and strings included); constructors, setup and
teardown, FOR TESTING, event handlers, redefinitions and interface implementations are never candidates; a public
method nobody calls is listed with the public note, not gated."""
import sys, unittest
from pathlib import Path

from helpers import KIT, install, project_cmd, temp_home

sys.path.insert(0, str(KIT / ".aix" / "scripts"))

FILES = {
    "src/zif_api.intf.abap": "INTERFACE zif_api PUBLIC.\n  METHODS go.\nENDINTERFACE.\n",
    "src/zcl_base.clas.abap": (
        "CLASS zcl_base DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    INTERFACES zif_api.\n    METHODS constructor.\n    METHODS run.\n    METHODS api_setter IMPORTING iv_x TYPE i.\n"
        "    METHODS on_change FOR EVENT changed OF zcl_util.\n    DATA mo_attr TYPE REF TO zcl_util.\n"
        "  PROTECTED SECTION.\n    METHODS also_never.\n  PRIVATE SECTION.\n    METHODS step.\n    METHODS step2.\n    METHODS helper.\n    METHODS never_called.\n    METHODS tested_only IMPORTING io_api TYPE REF TO zif_api.\n    METHODS in_template IMPORTING iv_n TYPE i.\n"
        "ENDCLASS.\nCLASS zcl_base IMPLEMENTATION.\n"
        "  METHOD constructor.\n  ENDMETHOD.\n"
        "  METHOD run.\n    DATA lo_api TYPE REF TO zif_api.\n    me->step( ).\n    helper( ).\n    zcl_util=>tool( ).\n    lo_api->go( ).\n    DATA(lo) = NEW zcl_util( ).\n    lo->other( ).\n"
        "    DATA(lo2) = zcl_util=>make( ).\n    lo2->other( ).\n    CALL METHOD me->step2.\n    mo_attr->other( ).\n    lo_unknown->mystery( ).\n    DATA(lv) = lines( mt_rows ).\n  ENDMETHOD.\n"
        "  METHOD api_setter.\n  ENDMETHOD.\n  METHOD on_change.\n  ENDMETHOD.\n  METHOD also_never.\n  ENDMETHOD.\n  METHOD step.\n  ENDMETHOD.\n  METHOD step2.\n  ENDMETHOD.\n"
        "  METHOD helper.\n  ENDMETHOD.\n  METHOD never_called.\n  ENDMETHOD.\n  METHOD tested_only.\n    io_api->go( ).\n  ENDMETHOD.\n  METHOD in_template.\n  ENDMETHOD.\n  METHOD zif_api~go.\n    DATA(lv) = |{ in_template(\n      iv_n = 1 ) }|.\n  ENDMETHOD.\nENDCLASS.\n"),
    "src/zcl_base.clas.testclasses.abap": "CLASS ltcl DEFINITION FOR TESTING.\n  PRIVATE SECTION.\n    METHODS test_it FOR TESTING.\nENDCLASS.\nCLASS ltcl IMPLEMENTATION.\n  METHOD test_it.\n    DATA lo TYPE REF TO zcl_base.\n    lo->tested_only( ).\n  ENDMETHOD.\nENDCLASS.\n",
    "src/zcl_sub.clas.abap": "CLASS zcl_sub DEFINITION PUBLIC INHERITING FROM zcl_base.\n  PUBLIC SECTION.\n    METHODS run REDEFINITION.\nENDCLASS.\nCLASS zcl_sub IMPLEMENTATION.\n  METHOD run.\n    super->run( ).\n  ENDMETHOD.\nENDCLASS.\n",
    "src/zcl_util.clas.abap": (
        "CLASS zcl_util DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    EVENTS changed.\n    CLASS-METHODS tool.\n    CLASS-METHODS make RETURNING VALUE(ro_util) TYPE REF TO zcl_util.\n    METHODS other.\n"
        "  PRIVATE SECTION.\n    METHODS priv_dyn.\n    METHODS priv_dead.\nENDCLASS.\nCLASS zcl_util IMPLEMENTATION.\n  METHOD tool.\n    DATA lv_name TYPE string.\n    lv_name = 'PRIV_DYN'.\n    CALL METHOD (lv_name).\n  ENDMETHOD.\n"
        "  METHOD make.\n  ENDMETHOD.\n  METHOD other.\n  ENDMETHOD.\n  METHOD priv_dyn.\n  ENDMETHOD.\n  METHOD priv_dead.\n  ENDMETHOD.\nENDCLASS.\n"),
    "src/zcl_impl2.clas.abap": "CLASS zcl_impl2 DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    INTERFACES zif_api.\nENDCLASS.\nCLASS zcl_impl2 IMPLEMENTATION.\n  METHOD zif_api~go.\n  ENDMETHOD.\nENDCLASS.\n",
    "src/zprog_rep.prog.abap": "REPORT zprog_rep.\nSTART-OF-SELECTION.\n  PERFORM calc.\n  CALL FUNCTION 'Z_FM'.\nFORM calc.\n  WRITE 'x'.\nENDFORM.\nFORM unused.\n  WRITE 'y'.\nENDFORM.\n",
    "src/zfg.fugr.z_fm.abap": "FUNCTION z_fm.\n  DATA lv TYPE i.\nENDFUNCTION.\n",
}


def plant(project: Path):
    for rel, text in FILES.items():
        (project / rel).parent.mkdir(parents=True, exist_ok=True)
        (project / rel).write_text(text, encoding="utf-8")


class AbapCallGraph(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        plant(self.project)

    def test_edges_resolve_through_known_targets_only(self):
        import abapcalls
        from pyfuncgraph import RESOLUTION
        RESOLUTION.update(seen=0, matched=0)
        nodes, edges = abapcalls.function_graph([str(self.project / "src")])
        short = {(a.split("/")[-1], b.split("/")[-1]) for a, b in edges}
        run = "zcl_base.clas.abap:run"
        for target in ("zcl_base.clas.abap:step", "zcl_base.clas.abap:helper", "zcl_util.clas.abap:tool", "zcl_base.clas.abap:zif_api~go", "zcl_impl2.clas.abap:zif_api~go",
                       "zcl_util.clas.abap:other", "zcl_util.clas.abap:make", "zcl_base.clas.abap:step2"):
            self.assertIn((run, target), short, f"{target}\n{sorted(short)}")
        self.assertIn(("zcl_sub.clas.abap:run", run), short, "super->run( )")
        self.assertIn(("zcl_base.clas.abap:tested_only", "zcl_base.clas.abap:zif_api~go"), short, "a parameter typed with the interface")
        self.assertFalse([e for e in short if "mystery" in e[1]], "an unknown receiver is never guessed")
        self.assertFalse([e for e in short if e[1].endswith(":lines")], "a built-in function is not a call")
        self.assertEqual((RESOLUTION["seen"], RESOLUTION["matched"]), (RESOLUTION["seen"], RESOLUTION["seen"] - 1), "exactly one unresolved call: lo_unknown->mystery( )")
        self.assertTrue(any(n.endswith("zcl_base.clas.testclasses.abap:ltcl.test_it") for n in nodes), "test methods are nodes, named by their local class")


class AbapDeadMethods(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        plant(self.project)
        install(self.home, self.project)

    def test_dead_methods_and_the_public_note(self):
        out = project_cmd(self.project, self.home, "code", "dead", "--functions", "src", check=False).stdout
        self.assertIn("src/zcl_base.clas.abap:never_called  (line", out, out)
        self.assertIn("src/zcl_base.clas.abap:also_never  (line", out, out)
        self.assertIn("src/zcl_util.clas.abap:priv_dead  (line", out, out)
        self.assertIn("src/zprog_rep.prog.abap:unused  (line", out, out)
        self.assertRegex(out, r"src/zcl_base\.clas\.abap:api_setter  \(line \d+\)  \(public", "a public method nobody calls carries the note")
        for live in ("constructor", "on_change", "zif_api~go", "tested_only", "priv_dyn", "step2", "zcl_sub.clas.abap:run", "test_it", "calc", "z_fm", ":run ", "in_template"):
            self.assertNotIn(live if ":" in live else f":{live}  (line", out, f"{live} is live\n" + out)
        self.assertIn("DEAD FUNCTIONS 5", out, out)

    def test_graph_functions_through_the_tool(self):
        out = project_cmd(self.project, self.home, "code", "graph", "--functions", "src", check=False).stdout
        self.assertIn("Dependency graph (functions", out, out)
        self.assertNotIn("Traceback", out)


if __name__ == "__main__":
    unittest.main()
