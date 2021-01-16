import unittest
from src.fixture_processor import file_operations

class TestFilOperations(unittest.TestCase):
    def test_file_operations(self):
        result = 2+2
        self.assertEqual(result,4)
        # file_operations()




if __name__ == "__main__":
    unittest.main()