import ast
from pathlib import Path

import pytest

from cfg import CFG

DATASET_DIR = Path(__file__).parent / "dataset"
DATASET_FILES = sorted(DATASET_DIR.glob("*.py"))


@pytest.mark.parametrize("source_file", DATASET_FILES)
def test_cfg(source_file: Path) -> None:
    expected_file = source_file.with_suffix(".cfg")
    assert expected_file.exists(), f"Missing compare file {expected_file.name}"
    expected = expected_file.read_text()

    python_file_ast = ast.parse(source_file.read_text())
    actual = str(CFG.from_ast(python_file_ast.body)) + "\n"

    assert actual == expected
