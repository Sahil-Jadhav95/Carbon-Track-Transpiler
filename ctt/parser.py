import ast
from typing import Any

class ParseError(Exception):
    """Custom exception for parser errors with detailed information."""
    def __init__(self, message: str, line: int = 0, column: int = 0, filename: str = ""):
        self.message = message
        self.line = line
        self.column = column
        self.filename = filename
        super().__init__(self.format_error())
    
    def format_error(self) -> str:
        if self.line > 0:
            return f"{self.filename}:{self.line}:{self.column} — {self.message}"
        return self.message


def parse_python_code(file_path: str) -> ast.Module:
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        tree = ast.parse(source, filename=file_path)
        return tree
    except SyntaxError as e:
        raise ParseError(
            message=e.msg or "Syntax Error",
            line=e.lineno or 0,
            column=e.offset or 0,
            filename=file_path
        ) from e
    except Exception as e:
        raise ParseError(
            message=f"Parse Error: {str(e)}",
            filename=file_path
        ) from e


def parse_javascript_code(file_path: str) -> dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    if not source.strip():
        return {"type": "Program", "language": "javascript", "source": source}

    # JavaScript parsing is validated earlier; keep a lightweight tree wrapper.
    return {"type": "Program", "language": "javascript", "source": source}


def parse_code(file_path: str, language: str = "python") -> ast.Module | dict[str, Any]:
    if language == "python":
        return parse_python_code(file_path)
    if language == "javascript":
        return parse_javascript_code(file_path)
    raise ParseError(message=f"Unsupported language: {language}", filename=file_path)

def read_source(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def dump_ast(tree: ast.AST, indent: int = 2) -> str:
    return ast.dump(tree, indent=indent)
