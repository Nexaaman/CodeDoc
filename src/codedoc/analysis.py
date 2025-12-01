import ast
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class Issue:
    code: str
    message: str
    line: int
    severity: str  # "LOW", "MEDIUM", "HIGH"

class StaticAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.issues: List[Issue] = []
        self.filename = ""

    def scan(self, code: str, filename: str = "") -> List[Issue]:
        """Parse and scan the code for static issues."""
        self.issues = []
        self.filename = filename
        try:
            tree = ast.parse(code)
            self.visit(tree)
        except SyntaxError as e:
            self.issues.append(Issue(
                code="SYNTAX_ERR",
                message=f"Syntax Error: {e.msg}",
                line=e.lineno or 0,
                severity="HIGH"
            ))
        return self.issues

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Rule: Missing Docstring
        if not ast.get_docstring(node) and len(node.body) > 1:
            self.issues.append(Issue(
                code="NO_DOC",
                message=f"Function '{node.name}' is missing a docstring.",
                line=node.lineno,
                severity="LOW"
            ))

        # Rule: Too many arguments (Simple complexity check)
        if len(node.args.args) > 6:
            self.issues.append(Issue(
                code="COMPLEXITY",
                message=f"Function '{node.name}' has {len(node.args.args)} arguments (max recommended: 6).",
                line=node.lineno,
                severity="MEDIUM"
            ))
            
        # Rule: Function too long
        func_len = node.end_lineno - node.lineno
        if func_len > 50:
             self.issues.append(Issue(
                code="COMPLEXITY",
                message=f"Function '{node.name}' is too long ({func_len} lines).",
                line=node.lineno,
                severity="LOW"
            ))

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        # Rule: Missing Docstring for Class
        if not ast.get_docstring(node):
            self.issues.append(Issue(
                code="NO_DOC",
                message=f"Class '{node.name}' is missing a docstring.",
                line=node.lineno,
                severity="LOW"
            ))
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # Rule: Broad Exception
        if node.type is None:  # bare except:
            self.issues.append(Issue(
                code="BROAD_EXCEPT",
                message="Avoid bare 'except:'. Catch specific errors instead.",
                line=node.lineno,
                severity="HIGH"
            ))
        elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
            self.issues.append(Issue(
                code="BROAD_EXCEPT",
                message="Catching generic 'Exception' can hide bugs.",
                line=node.lineno,
                severity="MEDIUM"
            ))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Rule: Print statements in code
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            self.issues.append(Issue(
                code="PRINT_STMT",
                message="Found 'print()' statement. Use logging instead?",
                line=node.lineno,
                severity="LOW"
            ))
        self.generic_visit(node)