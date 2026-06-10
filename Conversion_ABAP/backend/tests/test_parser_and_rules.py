from app.services.abap_parser import AbapParser
from app.services.rule_engine import RuleEngine


def test_parser_extracts_ast_cfg_and_dependencies():
    source = """
    SELECT SINGLE mandt carrid FROM sflight INTO TABLE lt_flights WHERE carrid = 'LH'.
    LOOP AT lt_flights INTO DATA(ls_flight).
      COLLECT ls_flight INTO lt_summary.
    ENDLOOP.
    CALL FUNCTION 'BAPI_FLIGHT_GETLIST'.
    """

    parsed = AbapParser().parse(source)

    assert parsed.ast.node_type == "program"
    assert parsed.annotations["contains_mandt"] is True
    assert "SFLIGHT" in parsed.dependency_graph["tables"]
    assert "BAPI_FLIGHT_GETLIST" in parsed.dependency_graph["function_modules"]
    assert parsed.control_flow_graph


def test_rule_engine_applies_enterprise_rewrites():
    source = "SELECT SINGLE MANDT carrid FROM sflight WHERE erdat = SY-DATUM AND time = SY-UZEIT."

    rewritten, rules, delta = RuleEngine().execute(source)

    assert "SELECT SINGLE" not in rewritten
    assert "MANDT" not in rewritten
    assert "CURRENT_DATE" in rewritten
    assert "CURRENT_TIME" in rewritten
    assert {rule.rule_name for rule in rules} >= {
        "select_single_limit",
        "sy_datum_current_date",
        "sy_uzeit_current_time",
        "remove_mandt_projection",
    }
    assert delta > 0

