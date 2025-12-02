import ast
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class Issue:
    code: str
    message: str
    line: int
    severity: str  # "LOW", "MEDIUM", "HIGH"

@dataclass
class FunctionMetric:
    name: str
    line: int
    complexity: int
    length: int
    args_count: int

class ComplexityVisitor(ast.NodeVisitor):
    """Calculates Cyclomatic Complexity (McCabe)."""
    def __init__(self):
        self.complexity = 1  # Base complexity is always 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_Try(self, node):
        self.complexity += len(node.handlers)
        self.generic_visit(node)
        
    def visit_FunctionDef(self, node):
        # Don't recurse into nested functions for the parent's complexity score
        pass 

class StaticAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.issues: List[Issue] = []
        self.metrics: List[FunctionMetric] = []
        self.filename = ""

    def scan(self, code: str, filename: str = "") -> Dict[str, Any]:
        """
        Parse and scan for static issues AND metrics.
        Returns a dict containing issues and metrics.
        """
        self.issues = []
        self.metrics = []
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
            
        return {
            "issues": self.issues,
            "metrics": self.metrics,
            "score": self._calculate_score()
        }

    def _calculate_score(self) -> int:
        """Calculate a 0-100 score based on found issues and metrics."""
        score = 100
        
        # Deduct for Issues
        severity_weights = {"HIGH": 10, "MEDIUM": 5, "LOW": 2}
        for issue in self.issues:
            score -= severity_weights.get(issue.severity, 2)

        # Deduct for Complexity & Code Style
        for m in self.metrics:
            if m.complexity > 10: score -= (m.complexity - 10) * 2
            if m.length > 50: score -= 2
            if m.args_count > 5: score -= 3

        return max(0, score)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # 1. Calculate Metrics
        calc = ComplexityVisitor()
        # We manually visit children of the function body to count complexity
        for child in node.body:
            calc.visit(child)
            
        func_len = node.end_lineno - node.lineno
        args_count = len(node.args.args)
        
        self.metrics.append(FunctionMetric(
            name=node.name,
            line=node.lineno,
            complexity=calc.complexity,
            length=func_len,
            args_count=args_count
        ))

        # 2. Rules Analysis
        # Rule: Complexity Check
        if calc.complexity > 10:
             self.issues.append(Issue(
                code="COMPLEXITY",
                message=f"Function '{node.name}' is too complex (Cyclomatic: {calc.complexity}). Refactor logic.",
                line=node.lineno,
                severity="MEDIUM"
            ))

        # Rule: Missing Docstring
        if not ast.get_docstring(node) and len(node.body) > 1:
            self.issues.append(Issue(
                code="NO_DOC",
                message=f"Function '{node.name}' is missing a docstring.",
                line=node.lineno,
                severity="LOW"
            ))

        # Rule: Too many arguments
        if args_count > 6:
            self.issues.append(Issue(
                code="ARGS",
                message=f"Function '{node.name}' has {args_count} arguments (max recommended: 6).",
                line=node.lineno,
                severity="LOW"
            ))
            
        # Rule: Function too long
        if func_len > 60:
             self.issues.append(Issue(
                code="LENGTH",
                message=f"Function '{node.name}' is too long ({func_len} lines).",
                line=node.lineno,
                severity="LOW"
            ))

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        if not ast.get_docstring(node):
            self.issues.append(Issue(
                code="NO_DOC",
                message=f"Class '{node.name}' is missing a docstring.",
                line=node.lineno,
                severity="LOW"
            ))
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if node.type is None:  # bare except:
            self.issues.append(Issue(
                code="BROAD_EXCEPT",
                message="Avoid bare 'except:'. Catch specific errors.",
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
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            self.issues.append(Issue(
                code="PRINT_STMT",
                message="Found 'print()' statement. Use logging instead?",
                line=node.lineno,
                severity="LOW"
            ))
        self.generic_visit(node)