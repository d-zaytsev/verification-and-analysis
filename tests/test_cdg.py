import ast
from pathlib import Path

import pytest

from cdg import CDG

DATASET_DIR = Path(__file__).parent / "dataset"
DATASET_FILES = sorted(DATASET_DIR.glob("*.py"))


@pytest.mark.parametrize("execution_number", range(5))
@pytest.mark.parametrize(
    "source_file", DATASET_FILES, ids=[f.stem for f in DATASET_FILES]
)
def test_cdg(source_file: Path, execution_number: int) -> None:
    expected_file = source_file.with_suffix(".cdg")
    assert expected_file.exists(), f"Missing compare file '{expected_file.name}'"
    expected = expected_file.read_text()

    python_file_ast = ast.parse(source_file.read_text())
    actual = str(CDG.from_ast(python_file_ast.body)) + "\n"

    assert actual == expected
