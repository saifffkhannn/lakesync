import json

from app.core.config import Settings
from app.schemas.conversion import SemanticContext
from app.services.abap_parser import AbapParser
from app.services.cortex_engine import CortexConversionEngine


class FlakyCortexConnector:
    def __init__(self):
        self.models: list[str] = []

    def execute(self, _sql, parameters=None):
        model = parameters["model"]
        self.models.append(model)
        if model == "deprecated-model":
            raise RuntimeError("model has been deprecated")
        return [
            {
                "response": json.dumps(
                    {
                        "sql": "SELECT * FROM SFLIGHT;",
                        "confidence": 0.91,
                        "warnings": [],
                        "assumptions": [],
                        "conversion_notes": ["Converted by Cortex."],
                        "artifact_type": "script",
                    }
                )
            }
        ]


def test_cortex_engine_skips_failed_model_and_uses_next():
    connector = FlakyCortexConnector()
    settings = Settings(cortex_model_priority=["deprecated-model", "openai-gpt-4.1"])
    parsed = AbapParser().parse("SELECT * FROM sflight.")

    output = CortexConversionEngine(connector, settings).convert(
        "SELECT * FROM sflight.",
        parsed,
        SemanticContext(),
        "SELECT * FROM sflight.",
    )

    assert connector.models == ["deprecated-model", "openai-gpt-4.1"]
    assert output.sql == "SELECT * FROM SFLIGHT;"


def test_cortex_engine_caps_confidence_when_core_behavior_is_omitted():
    connector = FlakyCortexConnector()
    settings = Settings(cortex_model_priority=["openai-gpt-4.1"])
    parsed = AbapParser().parse(
        """
        CALL FUNCTION 'AUTHORITY_CHECK_TCODE'.
        LOOP AT lt_items INTO DATA(ls_item).
          READ TABLE lt_lookup WITH KEY id = ls_item-id.
        ENDLOOP.
        """
    )

    def execute(_sql, parameters=None):
        connector.models.append(parameters["model"])
        return [
            {
                "response": json.dumps(
                    {
                        "sql": "SELECT * FROM AUDIT_VIEW;",
                        "confidence": 0.96,
                        "warnings": ["Authority checks require application layer implementation."],
                        "assumptions": [],
                        "conversion_notes": ["GUI behavior omitted."],
                        "artifact_type": "view",
                    }
                )
            }
        ]

    connector.execute = execute

    output = CortexConversionEngine(connector, settings).convert(
        "CALL FUNCTION 'AUTHORITY_CHECK_TCODE'.",
        parsed,
        SemanticContext(),
        "CALL FUNCTION 'AUTHORITY_CHECK_TCODE'.",
    )

    assert output.confidence == 0.65
    assert any("Confidence capped" in warning for warning in output.warnings)


def test_cortex_prompt_includes_learning_memory_examples():
    connector = FlakyCortexConnector()
    settings = Settings(cortex_model_priority=["openai-gpt-4.1"])
    parsed = AbapParser().parse("CALL FUNCTION 'AUTHORITY_CHECK_TCODE'.")
    context = SemanticContext(
        retrieved_patterns=[
            {
                "source_name": "z_auth.abap",
                "previous_gaps": ["Authority checks require application layer implementation."],
                "guidance": "Avoid repeating this gap.",
            }
        ]
    )

    prompts: list[str] = []

    def execute(_sql, parameters=None):
        prompts.append(parameters["prompt"])
        return [
            {
                "response": json.dumps(
                    {
                        "sql": "SELECT 'review required' AS conversion_note;",
                        "confidence": 0.5,
                        "warnings": ["Authority checks require application layer implementation."],
                        "assumptions": [],
                        "conversion_notes": [],
                        "artifact_type": "script",
                    }
                )
            }
        ]

    connector.execute = execute

    CortexConversionEngine(connector, settings).convert(
        "CALL FUNCTION 'AUTHORITY_CHECK_TCODE'.",
        parsed,
        context,
        "CALL FUNCTION 'AUTHORITY_CHECK_TCODE'.",
    )

    prompt = json.loads(prompts[0])
    assert prompt["learning_memory"][0]["source_name"] == "z_auth.abap"
