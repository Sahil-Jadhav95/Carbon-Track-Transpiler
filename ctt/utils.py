"""
Utility functions used across the CTT project.
"""

import os
import sys
from typing import Tuple


SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
}


def detect_language_from_path(file_path: str) -> str:
    _, ext = os.path.splitext(file_path.lower())
    return SUPPORTED_EXTENSIONS.get(ext, "")


def validate_file_with_language(file_path: str, language: str = "auto") -> Tuple[str, str]:
    abs_path = os.path.abspath(file_path)

    if not os.path.isfile(abs_path):
        print(f"Error: File not found: {abs_path}", file=sys.stderr)
        sys.exit(1)

    detected = detect_language_from_path(abs_path)
    if language == "auto":
        if not detected:
            print(f"Error: Unsupported file type: {abs_path}", file=sys.stderr)
            sys.exit(1)
        return abs_path, detected

    if language == "python" and not abs_path.endswith(".py"):
        print(f"Error: Not a Python file: {abs_path}", file=sys.stderr)
        sys.exit(1)

    if language == "javascript" and detected != "javascript":
        print(f"Error: Not a JavaScript file: {abs_path}", file=sys.stderr)
        sys.exit(1)

    return abs_path, language


def validate_file(file_path: str) -> str:
    """
    Validate that the given file path exists and is a Python file.

    Args:
        file_path: Path to check.

    Returns:
        Absolute path to the file.

    Raises:
        SystemExit: If validation fails.
    """
    abs_path, _ = validate_file_with_language(file_path, language="python")
    return abs_path


def print_section(title: str, content: str) -> None:
    """Print a formatted section with a title and content block."""
    print(f"\n## {title}\n")
    print(content)
    print()
