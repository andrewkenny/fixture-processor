import unittest
from src.fixture_processor.fixture_functions import fixture_maths

class TestFixtureMaths(unittest.TestCase):
    def test_fixture_maths(self):
        result = 2+2
        self.assertEqual(result,4)
        # fixture_maths()




if __name__ == "__main__":
    unittest.main()