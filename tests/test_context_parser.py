from pathlib import Path

import pytest

from parser.context_parser import ContextParser


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_external_context_file_with_values():
    context_file = FIXTURES / "sample_job.context"
    contexts = ContextParser(str(context_file)).parse()

    assert "Default" in contexts
    assert contexts["Default"]["env"] == "DEV"
    assert contexts["Default"]["timeout"] == "30"
    assert contexts["Prod"]["env"] == "PROD"


def test_context_parser_missing_file():
    with pytest.raises(FileNotFoundError):
        ContextParser("missing.context")
