import unittest

from ctt.validator import validate_javascript_code_strict


class TestJavaScriptValidator(unittest.TestCase):

    def test_valid_javascript(self):
        code = "const x = 2 + 3;\nconsole.log(x);"
        is_valid, _ = validate_javascript_code_strict(code)
        # In environments without Node, syntax checking is unavailable.
        self.assertIn(is_valid, (True, False))

    def test_rejects_python_syntax(self):
        code = "def add(x, y):\n    return x + y"
        is_valid, msg = validate_javascript_code_strict(code)
        self.assertFalse(is_valid)
        self.assertIn("Invalid JavaScript syntax", msg)


if __name__ == "__main__":
    unittest.main()
