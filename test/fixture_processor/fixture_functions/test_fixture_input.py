import unittest
from src.fixture_processor.fixture_functions import fixture_input

class TestFixtureInput(unittest.TestCase):
    def test_fixture_input(self):
        result = 2+2
        self.assertEqual(result,4)
        # fixture_input()
    



if __name__ == "__main__":
    unittest.main()