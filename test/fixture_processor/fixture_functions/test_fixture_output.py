import unittest
from src.fixture_processor.fixture_functions import fixture_output

class TestFixtureOutput(unittest.TestCase):
    def test_fixture_output(self):
        result = 2+2
        self.assertEqual(result,4)
        # fixture_output()




if __name__ == "__main__":
    unittest.main()