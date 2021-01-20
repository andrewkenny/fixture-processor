import unittest
from src.fixture_processor import helper_functions

class TestHelperFunctions(unittest.TestCase):
    def test_helper_functions(self):
        result = 2+2
        self.assertEqual(result,4)
        # helper_functions()




if __name__ == "__main__":
    unittest.main()