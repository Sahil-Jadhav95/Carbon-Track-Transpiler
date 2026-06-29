import unittest

from ctt.profiler import profile_code


class TestJavaScriptProfiler(unittest.TestCase):

    def test_javascript_profile_shape(self):
        source = "function f(){ return 1; }\nf();"
        hotspots = profile_code(source, language="javascript")

        self.assertIsInstance(hotspots, list)
        if hotspots:
            self.assertIn("function", hotspots[0])
            self.assertIn("time", hotspots[0])


if __name__ == "__main__":
    unittest.main()
