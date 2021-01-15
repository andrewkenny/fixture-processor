import unittest
from src.fixture_processor import fixture_processor_form

class TestFixtureProcessorForm(unittest.TestCase):
    def test_fixture_processor_form(self):
        result = 2+2
        self.assertEqual(result,4)
        # fixture_processor_form()




if __name__ == "__main__":
    unittest.main()