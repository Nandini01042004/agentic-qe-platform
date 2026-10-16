"""AST-based code analyzer for extracting interfaces, complexity, and risks."""

import ast
from typing import List, Dict, Any, Optional
from qualiagent.core.state import (
    FunctionArg,
    FunctionSpec,
    ClassSpec,
    CodebaseAnalysis,
)


class CyclomaticComplexityVisitor(ast.NodeVisitor):
    """Calculates McCabe Cyclomatic Complexity of a function AST node."""

    def __init__(self):
        self.complexity = 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        # Each boolean operator adds a decision path
        self.complexity += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_IfExp(self, node):  # Ternary expression: x if cond else y
        self.complexity += 1
        self.generic_visit(node)


class ExceptionVisitor(ast.NodeVisitor):
    """Identifies all explicitly raised exception names in a function."""

    def __init__(self):
        self.exceptions: List[str] = []

    def visit_Raise(self, node):
        if node.exc is not None:
            if isinstance(node.exc, ast.Name):
                self.exceptions.append(node.exc.id)
            elif isinstance(node.exc, ast.Call):
                if isinstance(node.exc.func, ast.Name):
                    self.exceptions.append(node.exc.func.id)
                elif isinstance(node.exc.func, ast.Attribute):
                    self.exceptions.append(node.exc.func.attr)
        self.generic_visit(node)


def parse_function_node(node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionSpec:
    """Parses a function or async function AST node into FunctionSpec."""
    # Arguments
    args: List[FunctionArg] = []
    defaults_offset = len(node.args.args) - len(node.args.defaults)

    for i, arg in enumerate(node.args.args):
        # Skip self / cls
        if arg.arg in ("self", "cls"):
            continue

        type_hint = ast.unparse(arg.annotation) if arg.annotation else "Any"
        default_val = None
        if i >= defaults_offset:
            default_index = i - defaults_offset
            if 0 <= default_index < len(node.args.defaults):
                default_val = ast.unparse(node.args.defaults[default_index])

        args.append(FunctionArg(name=arg.arg, type_hint=type_hint, default_val=default_val))

    # Return type
    return_type = ast.unparse(node.returns) if node.returns else "Any"

    # Docstring
    docstring = ast.get_docstring(node)

    # Cyclomatic Complexity
    cc_visitor = CyclomaticComplexityVisitor()
    cc_visitor.visit(node)

    # Raised exceptions
    exc_visitor = ExceptionVisitor()
    exc_visitor.visit(node)

    return FunctionSpec(
        name=node.name,
        args=args,
        return_type=return_type,
        docstring=docstring,
        raised_exceptions=list(set(exc_visitor.exceptions)),
        is_async=isinstance(node, ast.AsyncFunctionDef),
        cyclomatic_complexity=cc_visitor.complexity,
        line_start=node.lineno,
        line_end=getattr(node, "end_lineno", node.lineno),
    )


def analyze_python_source(code_str: str, file_path: str = "source.py") -> CodebaseAnalysis:
    """Analyzes Python source code using AST and generates CodebaseAnalysis metadata."""
    tree = ast.parse(code_str, filename=file_path)

    classes: List[ClassSpec] = []
    functions: List[FunctionSpec] = []
    imports: List[str] = []
    detected_risks: List[str] = []

    total_lines = len(code_str.splitlines())
    max_complexity = 1

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(ast.unparse(node))

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn_spec = parse_function_node(node)
            functions.append(fn_spec)
            max_complexity = max(max_complexity, fn_spec.cyclomatic_complexity)
            if fn_spec.cyclomatic_complexity >= 4:
                detected_risks.append(
                    f"High branch complexity in function '{fn_spec.name}' (Score: {fn_spec.cyclomatic_complexity})."
                )
            if fn_spec.raised_exceptions:
                detected_risks.append(
                    f"Function '{fn_spec.name}' raises explicit exceptions: {', '.join(fn_spec.raised_exceptions)}."
                )

        elif isinstance(node, ast.ClassDef):
            class_methods: List[FunctionSpec] = []
            class_attrs: List[str] = []

            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    m_spec = parse_function_node(item)
                    class_methods.append(m_spec)
                    max_complexity = max(max_complexity, m_spec.cyclomatic_complexity)
                    if m_spec.cyclomatic_complexity >= 4:
                        detected_risks.append(
                            f"High branch complexity in method '{node.name}.{m_spec.name}' (Score: {m_spec.cyclomatic_complexity})."
                        )
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    class_attrs.append(item.target.id)

            classes.append(
                ClassSpec(
                    name=node.name,
                    docstring=ast.get_docstring(node),
                    methods=class_methods,
                    attributes=class_attrs,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                )
            )

    # Estimate overall complexity
    if max_complexity <= 3:
        comp_str = "Low"
    elif max_complexity <= 7:
        comp_str = "Medium"
    else:
        comp_str = "High"

    module_name = file_path.replace("\\", "/").split("/")[-1].replace(".py", "")

    return CodebaseAnalysis(
        file_path=file_path,
        module_name=module_name,
        classes=classes,
        functions=functions,
        imports=imports,
        total_lines=total_lines,
        estimated_complexity=comp_str,
        detected_risks=detected_risks,
    )
