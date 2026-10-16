"""Unit tests for AST Parser and Complexity Analyzer."""

import pytest
from qualiagent.core.ast_parser import analyze_python_source


SAMPLE_CODE = """
def simple_add(a: int, b: int = 0) -> int:
    \"\"\"Adds two integers.\"\"\"
    return a + b

class Calculator:
    \"\"\"A calculator class.\"\"\"
    def divide(self, x: float, y: float) -> float:
        if y == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return x / y
"""


def test_ast_parses_functions_and_classes():
    analysis = analyze_python_source(SAMPLE_CODE, file_path="calc.py")
    assert analysis.module_name == "calc"
    assert len(analysis.functions) == 1
    assert len(analysis.classes) == 1

    fn = analysis.functions[0]
    assert fn.name == "simple_add"
    assert fn.return_type == "int"
    assert len(fn.args) == 2
    assert fn.args[1].default_val == "0"


def test_ast_detects_exceptions_and_branches():
    analysis = analyze_python_source(SAMPLE_CODE, file_path="calc.py")
    calc_cls = analysis.classes[0]
    assert calc_cls.name == "Calculator"
    assert len(calc_cls.methods) == 1

    divide_m = calc_cls.methods[0]
    assert divide_m.name == "divide"
    assert "ZeroDivisionError" in divide_m.raised_exceptions
    assert divide_m.cyclomatic_complexity >= 2
