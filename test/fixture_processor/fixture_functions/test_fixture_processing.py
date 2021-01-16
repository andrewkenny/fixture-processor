import unittest
from src.fixture_processor.fixture_functions import fixture_processing

class TestFixturepfixtureProcessing(unittest.TestCase):
    def test_fixture_processing(self):
        result = 2+2
        self.assertEqual(result,4)
        # fixture_processing()




if __name__ == "__main__":
    unittest.main()