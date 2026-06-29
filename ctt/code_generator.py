import ast
from typing import Any

def generate_code(tree: ast.Module | dict[str, Any] | str, language: str = "python") -> str:
    if language == "python":
        return ast.unparse(tree)  # type: ignore[arg-type]

    if language == "javascript":
        if isinstance(tree, str):
            return tree
        if isinstance(tree, dict):
            return str(tree.get("source", ""))
        return ""

    raise ValueError(f"Unsupported language: {language}")

def generate_code_to_file(
    tree: ast.Module | dict[str, Any] | str,
    output_path: str,
    language: str = "python",
) -> str:

    code = generate_code(tree, language=language)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code)
        f.write("\n")
    return code
 