import ast
import unittest

from ctt.optimizer import (
    ConstantFoldingTransformer,
    StrengthReductionTransformer,
    RedundantAssignmentRemover,
    optimize_ast,
)


class TestConstantFolding(unittest.TestCase):
    """Tests for the constant folding transformer."""

    def _fold(self, expr: str) -> str:
        tree = ast.parse(expr, mode="eval")
        transformer = ConstantFoldingTransformer()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)
        return ast.unparse(new_tree)

    def test_addition(self):
        self.assertEqual(self._fold("2 + 3"), "5")

    def test_multiplication(self):
        self.assertEqual(self._fold("2 * 3"), "6")

    def test_subtraction(self):
        self.assertEqual(self._fold("10 - 4"), "6")

    def test_nested(self):
        # (2 + 3) * 4 → 5 * 4 → 20
        self.assertEqual(self._fold("(2 + 3) * 4"), "20")

    def test_no_fold_with_variable(self):
        result = self._fold("x + 1")
        self.assertIn("x", result)

    def test_floor_division(self):
        self.assertEqual(self._fold("10 // 3"), "3")

    def test_division_by_zero_not_folded(self):
        result = self._fold("10 // 0")
        self.assertEqual(result, "10 // 0")


class TestStrengthReduction(unittest.TestCase):
    """Tests for the strength reduction transformer."""

    def _reduce(self, code: str) -> str:
        tree = ast.parse(code)
        transformer = StrengthReductionTransformer()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)
        return ast.unparse(new_tree)

    def test_square(self):
        result = self._reduce("y = x ** 2")
        self.assertEqual(result, "y = x * x")

    def test_cube(self):
        result = self._reduce("y = x ** 3")
        self.assertEqual(result, "y = x * x * x")

    def test_power_of_4(self):
        result = self._reduce("y = x ** 4")
        self.assertEqual(result, "y = x * x * x * x")

    def test_large_exponent_not_reduced(self):
        result = self._reduce("y = x ** 10")
        self.assertEqual(result, "y = x ** 10")

    def test_non_integer_exponent_not_reduced(self):
        result = self._reduce("y = x ** 0.5")
        self.assertEqual(result, "y = x ** 0.5")


class TestRedundantAssignmentRemoval(unittest.TestCase):
    """Tests for redundant assignment removal."""

    def _remove(self, code: str) -> str:
        tree = ast.parse(code)
        transformer = RedundantAssignmentRemover()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)
        return ast.unparse(new_tree)

    def test_simple_redundant(self):
        code = "x = 5\nx = 10"
        result = self._remove(code)
        self.assertEqual(result, "x = 10")

    def test_no_redundancy(self):
        code = "x = 5\ny = 10"
        result = self._remove(code)
        self.assertIn("x = 5", result)
        self.assertIn("y = 10", result)

    def test_different_variables(self):
        code = "a = 1\nb = 2\na = 3"
        result = self._remove(code)
        self.assertIn("b = 2", result)
        self.assertIn("a = 3", result)


class TestFullOptimization(unittest.TestCase):
    """Integration tests for the full optimize_ast pipeline."""

    def test_combined(self):
        code = """\
x = 2 * 3
y = x ** 2
z = 0
z = 42
"""
        tree = ast.parse(code)
        optimized_tree, records = optimize_ast(tree)
        result = ast.unparse(optimized_tree)

        # Constant folding: 2 * 3 → 6
        self.assertIn("x = 6", result)
        # Strength reduction: x ** 2 → x * x
        self.assertIn("x * x", result)
        # Redundant removal: z = 0 removed
        self.assertNotIn("z = 0", result)
        self.assertIn("z = 42", result)

        # Should have recorded optimizations
        self.assertGreater(len(records), 0)


class TestExtendedOptimizationRules(unittest.TestCase):
    """Tests for optional extended optimization rules."""

    def test_loop_fusion_applies_in_default_pipeline(self):
        code = """\
for i in range(3):
    x = i
for i in range(3):
    y = i * 2
"""
        tree = ast.parse(code)

        optimized_tree, records = optimize_ast(tree)
        optimized_result = ast.unparse(optimized_tree)
        self.assertEqual(optimized_result.count("for i in range(3):"), 1)
        self.assertTrue(any("Loop fusion" in r.description for r in records))

    def test_variable_inlining_return(self):
        code = """\
def f(x):
    temp = x + 5
    return temp
"""
        tree = ast.parse(code)
        optimized_tree, records = optimize_ast(tree)
        result = ast.unparse(optimized_tree)

        self.assertIn("return x + 5", result)
        self.assertNotIn("temp = x + 5", result)
        self.assertTrue(any("Variable inlining" in r.description for r in records))

    def test_string_concat_to_join(self):
        code = """\
s = ''
for ch in items:
    s += ch
"""
        tree = ast.parse(code)
        optimized_tree, records = optimize_ast(tree)
        result = ast.unparse(optimized_tree)

        self.assertIn("s = ''.join(items)", result)
        self.assertTrue(any("String optimization" in r.description for r in records))


if __name__ == "__main__":
    unittest.main()
