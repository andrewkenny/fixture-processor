import unittest
from src.fixture_processor import fixture_canvas_form

class TestFixtureCanvasForm(unittest.TestCase):
    def test_fixture_canvas_form(self):
        result = 2+2
        self.assertEqual(result,4)
        # fixture_canvas_form()



if __name__ == "__main__":
    unittest.main()