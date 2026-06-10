"""Lightweight ABAP parser for conversion context.

This parser does not try to fully compile ABAP. It extracts enough structure for conversion:
statement types, dependency hints, feature counts, control-flow links, and annotations.
"""

import re
from collections import defaultdict

from app.schemas.conversion import AstNode, ParsedProgram


class AbapParser:
    """Builds a typed, conversion-oriented representation of ABAP source."""

    statement_patterns = {
        "select": re.compile(r"\bSELECT\b(?P<body>.*?)\.", re.IGNORECASE | re.DOTALL),
        "loop": re.compile(r"\bLOOP\s+AT\s+(?P<table>\w+).*?\.", re.IGNORECASE | re.DOTALL),
        "read_table": re.compile(r"\bREAD\s+TABLE\s+(?P<table>\w+).*?\.", re.IGNORECASE | re.DOTALL),
        "collect": re.compile(r"\bCOLLECT\s+(?P<value>\w+).*?\.", re.IGNORECASE | re.DOTALL),
        "append": re.compile(r"\bAPPEND\s+(?P<value>\w+).*?\.", re.IGNORECASE | re.DOTALL),
        "modify": re.compile(r"\bMODIFY\s+(?P<table>\w+).*?\.", re.IGNORECASE | re.DOTALL),
        "delete": re.compile(r"\bDELETE\s+(?P<table>\w+).*?\.", re.IGNORECASE | re.DOTALL),
        "call_function": re.compile(r"\bCALL\s+FUNCTION\s+'(?P<name>[^']+)'.*?\.", re.IGNORECASE | re.DOTALL),
        "class": re.compile(r"\bCLASS\s+(?P<name>\w+)\s+DEFINITION\b", re.IGNORECASE),
        "method": re.compile(r"\bMETHOD\s+(?P<name>\w+)\b", re.IGNORECASE),
    }
    table_pattern = re.compile(r"\b(?:FROM|JOIN|UPDATE|INTO\s+TABLE|MODIFY|DELETE)\s+(?P<table>[A-Z0-9_/]+)", re.IGNORECASE)

    def parse(self, source: str) -> ParsedProgram:
        """Parse ABAP source into AST, dependency, control-flow, and annotation models."""
        root = AstNode(node_type="program", value="ABAP_PROGRAM", line=1)
        control_flow: dict[str, list[str]] = defaultdict(list)
        dependencies: dict[str, list[str]] = defaultdict(list)
        statements = self._split_statements(source)

        previous_id: str | None = None
        feature_counts: dict[str, int] = defaultdict(int)
        for index, statement in enumerate(statements, start=1):
            node = self._parse_statement(statement, source)
            statement_id = f"{index}:{node.node_type}"
            root.children.append(node)
            feature_counts[node.node_type] += 1
            if previous_id:
                control_flow[previous_id].append(statement_id)
            previous_id = statement_id
            for table in self.table_pattern.findall(statement):
                dependencies["tables"].append(table.upper())
            for function in re.findall(r"CALL\s+FUNCTION\s+'([^']+)'", statement, re.IGNORECASE):
                dependencies["function_modules"].append(function.upper())

        dependencies = {key: sorted(set(values)) for key, values in dependencies.items()}
        return ParsedProgram(
            ast=root,
            control_flow_graph=dict(control_flow),
            dependency_graph=dependencies,
            annotations={
                "feature_counts": dict(feature_counts),
                "contains_mandt": bool(re.search(r"\bMANDT\b", source, re.IGNORECASE)),
                "contains_for_all_entries": bool(re.search(r"FOR\s+ALL\s+ENTRIES", source, re.IGNORECASE)),
            },
        )

    def _split_statements(self, source: str) -> list[str]:
        """Split source into ABAP statements while preserving the original starting line."""
        statements = []
        current = []
        for line_number, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("*"):
                continue
            current.append((line_number, stripped))
            if stripped.endswith("."):
                first_line = current[0][0]
                body = " ".join(part for _, part in current)
                statements.append(f"@line:{first_line} {body}")
                current = []
        if current:
            first_line = current[0][0]
            body = " ".join(part for _, part in current)
            statements.append(f"@line:{first_line} {body}")
        return statements

    def _parse_statement(self, statement: str, full_source: str) -> AstNode:
        """Classify one statement and capture useful regex groups for downstream conversion."""
        line_match = re.match(r"@line:(?P<line>\d+)\s+(?P<body>.*)", statement, re.DOTALL)
        line = int(line_match.group("line")) if line_match else 1
        body = line_match.group("body") if line_match else statement
        for node_type, pattern in self.statement_patterns.items():
            match = pattern.search(body)
            if match:
                return AstNode(
                    node_type=node_type,
                    value=self._compact(body),
                    line=line,
                    annotations={
                        "captures": {key: value for key, value in match.groupdict().items() if value},
                        "uses_field_symbols": "FIELD-SYMBOL" in full_source.upper(),
                    },
                )
        return AstNode(node_type="statement", value=self._compact(body), line=line)

    def _compact(self, value: str) -> str:
        """Collapse whitespace so AST values are compact and readable."""
        return re.sub(r"\s+", " ", value).strip()
