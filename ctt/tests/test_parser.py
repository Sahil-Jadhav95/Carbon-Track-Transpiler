import ast
import os
import unittest
import tempfile

from ctt.parser import parse_code, read_source, dump_ast, ParseError


SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_code")
EXAMPLE_FILE = os.path.join(SAMPLE_DIR, "example.py")


class TestParser(unittest.TestCase):

    def test_parse_code_returns_module(self):
        tree = parse_code(EXAMPLE_FILE)
        self.assertIsInstance(tree, ast.Module)

    def test_parse_code_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            parse_code("nonexistent_file.py")

    def test_read_source(self):
        source = read_source(EXAMPLE_FILE)
        self.assertIn("def compute_square", source)

    def test_dump_ast(self):
        tree = parse_code(EXAMPLE_FILE)
        dumped = dump_ast(tree)
        self.assertIn("Module", dumped)


class TestParserSyntaxError(unittest.TestCase):

    def test_invalid_syntax(self):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        )
        tmp.write("def broken(\n")
        tmp.close()
        try:
            with self.assertRaises(ParseError):
                parse_code(tmp.name)
        finally:
            os.unlink(tmp.name)


class TestJavaScriptParser(unittest.TestCase):

    def test_parse_javascript_returns_program_wrapper(self):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", delete=False, encoding="utf-8"
        )
        tmp.write("const x = 2 + 3;\nconsole.log(x);\n")
        tmp.close()

        try:
            tree = parse_code(tmp.name, language="javascript")
            self.assertIsInstance(tree, dict)
            self.assertEqual(tree.get("type"), "Program")
            self.assertIn("console.log", tree.get("source", ""))
        finally:
            os.unlink(tmp.name)


if __name__ == "__main__":
    unittest.main()
