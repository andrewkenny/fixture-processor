@REM @echo off

@REM DIR: tests.fixture_processor
start python -m unittest tests.fixture_processor.test_file_operations
start python -m unittest tests.fixture_processor.test_fixture_canvas_form
start python -m unittest tests.fixture_processor.test_fixture_processor_form
start python -m unittest tests.fixture_processor.test_helper_functions

@REM DIR: tests.fixture_processor.fixture_functions
start python -m unittest tests.fixture_processor.fixture_functions.test_extract_wires
start python -m unittest tests.fixture_processor.fixture_functions.test_fixture_input
start python -m unittest tests.fixture_processor.fixture_functions.test_fixture_maths
start python -m unittest tests.fixture_processor.fixture_functions.test_fixture_modifications
start python -m unittest tests.fixture_processor.fixture_functions.test_fixture_output
start python -m unittest tests.fixture_processor.fixture_functions.test_fixture_processing
start python -m unittest tests.fixture_processor.fixture_functions.test_output_data

@REM DIR: tests.fixture_processor.options_lib
start python -m unittest tests.fixture_processor.options_lib.test_fixture_processing_options
start python -m unittest tests.fixture_processor.options_lib.test_option_functions
start python -m unittest tests.fixture_processor.options_lib.test_program_options

