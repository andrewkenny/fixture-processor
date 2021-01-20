import unittest
from src.fixture_processor.fixture_functions import output_data

class TestOutputData(unittest.TestCase):
    def test_output_data(self):
        result = 2+2
        self.assertEqual(result,4)
        # output_data()




if __name__ == "__main__":
    unittest.main()