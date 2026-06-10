from app.schemas.conversion import SemanticContext
from app.services.abap_parser import AbapParser
from app.services.local_sql_converter import LocalSqlConverter


def test_local_converter_turns_select_single_into_snowflake_limit():
    source = "SELECT SINGLE mandt carrid FROM sflight INTO @DATA(lv_carrid) WHERE erdat = SY-DATUM."
    parsed = AbapParser().parse(source)

    output = LocalSqlConverter().convert(source, parsed, SemanticContext())

    assert "SELECT carrid FROM sflight" in output.sql
    assert "CURRENT_DATE" in output.sql
    assert "LIMIT 1" in output.sql
    assert "MANDT" not in output.sql


def test_local_converter_marks_internal_table_logic_for_review():
    source = """
    LOOP AT lt_items INTO DATA(ls_item).
      COLLECT ls_item INTO lt_summary.
    ENDLOOP.
    """
    parsed = AbapParser().parse(source)

    output = LocalSqlConverter().convert(source, parsed, SemanticContext())

    assert "ABAP internal table loop" in output.sql
    assert output.confidence < 0.7
