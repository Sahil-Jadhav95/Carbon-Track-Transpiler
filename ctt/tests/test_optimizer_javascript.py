import unittest

from ctt.optimizer_javascript import optimize_javascript_source


class TestJavaScriptOptimizer(unittest.TestCase):

    def test_applies_basic_optimizations(self):
        source = """
const a = 2 + 3;
let b = a * 1;
if (flag === true) {
  console.log(b);
}
""".strip()
        optimized, records = optimize_javascript_source(source, mode="both")

        self.assertIn("const a = 5;", optimized)
        self.assertIn("let b = a;", optimized)
        self.assertIn("if (flag)", optimized)
        self.assertGreater(len(records), 0)

    def test_strength_reduction(self):
        source = "const value = x ** 3;"
        optimized, _ = optimize_javascript_source(source, mode="energy")
        self.assertIn("x * x * x", optimized)

    def test_dead_code_elimination(self):
        source = """
function f() {
  return 1;
  console.log('dead');
}
""".strip()
        optimized, records = optimize_javascript_source(source, mode="general")
        self.assertNotIn("dead", optimized)
        self.assertTrue(any("Dead code elimination" in record.description for record in records))

    def test_variable_inlining(self):
        source = """
function f(x) {
  const temp = x + 5;
  return temp;
}
""".strip()
        optimized, records = optimize_javascript_source(source, mode="general")
        self.assertIn("return x + 5;", optimized)
        self.assertNotIn("temp =", optimized)
        self.assertTrue(any("Variable inlining" in record.description for record in records))

    def test_common_subexpression_reuse(self):
        source = """
const a = x + 1;
const b = x + 1;
""".strip()
        optimized, records = optimize_javascript_source(source, mode="general")
        self.assertIn("const b = a;", optimized)
        self.assertTrue(any("Common subexpression reuse" in record.description for record in records))

    def test_loop_fusion(self):
        source = """
for (let i of items) {
  first.push(i);
}
for (let i of items) {
  second.push(i);
}
""".strip()
        optimized, records = optimize_javascript_source(source, mode="general")
        self.assertEqual(optimized.count("for (let i of items)"), 1)
        self.assertTrue(any("Loop fusion" in record.description for record in records))

    def test_string_concat_to_join(self):
        source = """
let out = "";
for (const ch of items) {
  out += ch;
}
""".strip()
        optimized, records = optimize_javascript_source(source, mode="general")
        self.assertIn("out = items.join", optimized)
        self.assertTrue(any("String optimization" in record.description for record in records))


if __name__ == "__main__":
    unittest.main()
