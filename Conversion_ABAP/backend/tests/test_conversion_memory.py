from app.schemas.conversion import ConversionOutput, SemanticContext
from app.services.abap_parser import AbapParser
from app.services.conversion_memory import ConversionMemory


def test_conversion_memory_stores_unresolved_gaps_and_retrieves_similar_examples(tmp_path):
    memory = ConversionMemory(tmp_path / "memory.jsonl")
    source = "CALL FUNCTION 'AUTHORITY_CHECK_TCODE'. SELECT * FROM usr02."
    parsed = AbapParser().parse(source)
    output = ConversionOutput(
        sql="SELECT * FROM USR02;",
        confidence=0.42,
        warnings=["Authority checks require application layer implementation."],
        assumptions=[],
        conversion_notes=["CALL FUNCTION cannot be directly converted to Snowflake SQL."],
    )

    entry = memory.store("z_auth.abap", source, output, parsed, SemanticContext())
    examples = memory.retrieve("CALL FUNCTION 'AUTHORITY_CHECK_TCODE'.", parsed)

    assert entry is not None
    assert memory.path.exists()
    assert examples
    assert "previous_gaps" in examples[0]
    assert "Authority checks require application layer implementation." in examples[0]["previous_gaps"]
