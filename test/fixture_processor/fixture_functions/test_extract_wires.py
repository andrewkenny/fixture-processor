import unittest
from src.fixture_processor.fixture_functions import extract_wires

class TestExtractWires(unittest.TestCase):
    def test_extract_wires(self):
        result = 2+2
        self.assertEqual(result,4)
        # extract_wires()




if __name__ == "__main__":
    unittest.main()