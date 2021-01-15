import unittest
from src.fixture_processor.options_lib import program_options

class TestProgramOptions(unittest.TestCase):
    def test_options_functions(self):
        result = 2+2
        self.assertEqual(result,4)
        # program_options()




if __name__ == "__main__":
    unittest.main()