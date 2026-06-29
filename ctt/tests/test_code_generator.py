"""
Unit tests for the CTT code generator module.
"""

import ast
import unittest

from ctt.code_generator import generate_code


class TestCodeGenerator(unittest.TestCase):

    def test_round_trip(self):
        """Ensure code → AST → code produces valid Python."""
        original = "x = 2 + 3\nprint(x)"
        tree = ast.parse(original)
        result = generate_code(tree)
        # Should be parseable Python
        ast.parse(result)
        self.assertIn("x = 2 + 3", result)
        self.assertIn("print(x)", result)

    def test_empty_module(self):
        tree = ast.parse("")
        result = generate_code(tree)
        self.assertEqual(result.strip(), "")

    def test_javascript_passthrough_from_string(self):
        source = "const x = 2 + 3;"
        result = generate_code(source, language="javascript")
        self.assertEqual(result, source)

    def test_javascript_passthrough_from_program_wrapper(self):
        source = "let value = 10;"
        tree = {"type": "Program", "source": source}
        result = generate_code(tree, language="javascript")
        self.assertEqual(result, source)


if __name__ == "__main__":
    unittest.main()
