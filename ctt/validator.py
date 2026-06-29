"""
Strict Python-only input validation module for Carbon-Track Transpiler.

Provides a 3-layer validation system:
1. AST Syntax Validation — checks if code parses as valid Python
2. Forbidden Pattern Detection — rejects non-Python code markers
3. Python Structure Detection — ensures code looks like Python
"""

import ast
import re
import shutil
import subprocess
import tempfile
from typing import Tuple


def is_valid_python_syntax(code: str) -> bool:
    """
    Check if code is valid Python syntax using AST parsing.
    
    Args:
        code: Source code string to validate
        
    Returns:
        True if code parses successfully, False otherwise
    """
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def contains_forbidden_patterns(code: str) -> Tuple[bool, str]:
    """
    Detect non-Python code markers and reject them.
    
    Rejects:
    - JavaScript keywords: function, var, let, const, console.log, =>
    - C/C++ markers: #include, public static void, using namespace
    - Semicolon-terminated statements
    - Curly braces (common in C, JS) — but NOT f-strings or dict literals
    - Main function patterns
    
    Args:
        code: Source code string to validate
        
    Returns:
        Tuple of (found_forbidden, description) where found_forbidden is True if
        any forbidden pattern is detected
    """
    forbidden_patterns = {
        r"^\s*function\b": "JavaScript 'function' keyword detected",
        r"^\s*var\b": "JavaScript 'var' keyword detected",
        r"^\s*let\b": "JavaScript 'let' keyword detected",
        r"^\s*const\b": "JavaScript 'const' keyword detected",
        r"console\.log\s*\(": "JavaScript 'console.log' detected",
        r"=>": "JavaScript arrow function '=>' detected",
        r"^\s*#include\b": "C preprocessor '#include' detected",
        r"using\s+namespace\b": "C++ 'using namespace' detected",
        r"public\s+static\s+void\b": "Java/C# method signature detected",
        r"\bvoid\s+main\s*\(": "C-style void main detected",
        r"\bint\s+main\s*\(": "C-style int main detected",
    }
    
    for pattern, description in forbidden_patterns.items():
        if re.search(pattern, code, re.IGNORECASE):
            return True, description
    
    # Check for block-level curly braces (C/Java/JS style)
    # This pattern looks for standalone curly braces OR braces surrounding code
    # But excludes f-strings and dict literals
    # Valid patterns to exclude: f"{var}", {key: value}
    # Invalid patterns to catch: { code } with newlines
    block_brace_pattern = r'\n\s*\{[^\n]*\n'  # Multiline blocks with braces
    if re.search(block_brace_pattern, code):
        return True, "Curly brace blocks detected (C/Java/JS style)"
    
    # Check for semicolon-terminated common statements (strong C/Java/JS indicator)
    lines_with_semicolons = [line.strip() for line in code.split('\n')
                             if line.strip().endswith(';')
                             and not line.strip().startswith('#')
                             and not line.strip().startswith('"""')
                             and not line.strip().startswith("'''")
                             and not re.match(r"^\s*(for|if|while|def|class)\b", line.strip())]
    if lines_with_semicolons:
        semicolon_ratio = len(lines_with_semicolons) / max(len(code.split('\n')), 1)
        if semicolon_ratio > 0.2:  # More than 20% of lines have semicolons
            return True, "Too many semicolon-terminated lines detected (C/Java/JS style)"
    
    return False, ""


def looks_like_python_structure(code: str) -> Tuple[bool, str]:
    """
    Ensure code contains Python-like structural elements.
    
    This is a secondary filter to catch obviously non-Python code.
    Since Layer 1 already validates Python syntax, this just detects
    cases where code might parse but looks like corrupted data.
    
    Checks for presence of Python keywords and structures:
    - Control flow: def, for, while, if, else, elif
    - I/O: print()
    - Imports: import, from
    - Colons (Python block delimiters)
    
    Args:
        code: Source code string to validate
        
    Returns:
        Tuple of (looks_like_python, description) where looks_like_python is True if
        code appears to be Python or is empty/short
    """
    # Empty code is acceptable (will be caught later)
    if code.strip() == "":
        return True, ""
    
    python_patterns = [
        (r"^\s*def\s+[A-Za-z_][A-Za-z0-9_]*\s*\(", "function definition"),
        (r"^\s*for\s+", "for loop"),
        (r"^\s*while\s+", "while loop"),
        (r"^\s*if\s+", "if statement"),
        (r"\bprint\s*\(", "print function"),
        (r"^\s*(from\s+\w+\s+import\s+|import\s+)", "import statement"),
        (r":\s*$", "block colon"),
        (r"=\s*[^=]", "assignment operator"),  # Simple variable assignment
    ]
    
    matches = 0
    
    for pattern, description in python_patterns:
        if re.search(pattern, code, re.MULTILINE):
            matches += 1
    
    # Only reject if code looks completely non-Python (no Python markers at all)
    # Since Layer 1 already validated syntax, we just catch obvious non-Python cases
    # Accept: any code with 1+ Python markers, or assignments
    if matches >= 1:
        return True, ""
    
    # Very short code without markers could be a single literal or expression
    # Accept if it's < 50 chars (likely valid single-line Python like: x=5, "hello", etc)
    if len(code.strip()) < 50 and not re.search(r'\n', code):
        return True, ""
    
    # Only reject if code is longer AND has no Python markers AND no assignments
    return False, "Code does not contain Python structural features (def, for, if, import, print, etc.)"


def validate_python_code_strict(code: str) -> Tuple[bool, str]:
    """
    Strict 3-layer validation of Python code.
    
    Validates:
    1. Syntax — code must parse as valid Python
    2. Forbidden patterns — no C/Java/JS markers
    3. Python structure — code must look like Python
    
    Args:
        code: Source code string to validate
        
    Returns:
        Tuple of (is_valid, message) where is_valid is True if all checks pass
    """
    # Layer 1: Check syntax
    if not is_valid_python_syntax(code):
        return False, "❌ Invalid Python syntax — code does not parse"
    
    # Layer 2: Forbidden patterns
    has_forbidden, forbidden_msg = contains_forbidden_patterns(code)
    if has_forbidden:
        return False, f"❌ Non-Python code detected — {forbidden_msg}"
    
    # Layer 3: Python structure
    looks_python, structure_msg = looks_like_python_structure(code)
    if not looks_python:
        return False, f"❌ {structure_msg}"
    
    return True, "✅ Valid Python code"


def is_valid_javascript_syntax(code: str) -> bool:
    """Validate JavaScript syntax with Node.js if available."""
    node_path = shutil.which("node")
    if not node_path:
        return False

    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False, encoding="utf-8") as tmp:
        tmp.write(code)
        temp_name = tmp.name

    try:
        result = subprocess.run(
            [node_path, "--check", temp_name],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0
    except Exception:
        return False
    finally:
        try:
            import os
            os.unlink(temp_name)
        except OSError:
            pass


def contains_forbidden_javascript_patterns(code: str) -> Tuple[bool, str]:
    forbidden_patterns = {
        r"^\s*def\s+": "Python 'def' keyword detected",
        r"\bprint\s*\(": "Python 'print()' usage detected",
        r"^\s*from\s+\w+\s+import\s+": "Python import syntax detected",
        r"^\s*import\s+\w+\s*$": "Python bare import syntax detected",
        r"^\s*#include\b": "C preprocessor '#include' detected",
        r"using\s+namespace\b": "C++ 'using namespace' detected",
    }

    for pattern, description in forbidden_patterns.items():
        if re.search(pattern, code, re.IGNORECASE | re.MULTILINE):
            return True, description

    return False, ""


def looks_like_javascript_structure(code: str) -> Tuple[bool, str]:
    if code.strip() == "":
        return True, ""

    javascript_patterns = [
        r"\bfunction\s+[A-Za-z_$][A-Za-z0-9_$]*\s*\(",
        r"\b(const|let|var)\s+[A-Za-z_$][A-Za-z0-9_$]*\s*=",
        r"=>",
        r"\bconsole\.log\s*\(",
        r"\bif\s*\(",
        r"\bfor\s*\(",
        r"\{",
        r";\s*$",
    ]

    for pattern in javascript_patterns:
        if re.search(pattern, code, re.MULTILINE):
            return True, ""

    if len(code.strip()) < 50 and "\n" not in code:
        return True, ""

    return False, "Code does not contain JavaScript structural features"


def validate_javascript_code_strict(code: str) -> Tuple[bool, str]:
    if not is_valid_javascript_syntax(code):
        return False, "❌ Invalid JavaScript syntax (or Node.js is unavailable for syntax validation)"

    has_forbidden, forbidden_msg = contains_forbidden_javascript_patterns(code)
    if has_forbidden:
        return False, f"❌ Non-JavaScript code detected — {forbidden_msg}"

    looks_js, structure_msg = looks_like_javascript_structure(code)
    if not looks_js:
        return False, f"❌ {structure_msg}"

    return True, "✅ Valid JavaScript code"


def validate_code_strict(code: str, language: str) -> Tuple[bool, str]:
    if language == "python":
        return validate_python_code_strict(code)
    if language == "javascript":
        return validate_javascript_code_strict(code)
    return False, f"❌ Unsupported language: {language}"
