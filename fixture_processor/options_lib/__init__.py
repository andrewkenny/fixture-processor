
from fixture_processor.options_lib.options_functions import generate_option_functions

# import the program options
from fixture_processor.options_lib.program_options import get_section_comments as _get_prog_section_comments
from fixture_processor.options_lib.program_options import get_options as _get_program_options

# import the user options.
from fixture_processor.options_lib.fixture_processing_options import get_section_comments as _get_fp_section_comments
from fixture_processor.options_lib.fixture_processing_options import get_options as _get_fp_options

# from fixture_processor import fixture_processing_options

program_option_functions = generate_option_functions(_get_prog_section_comments(),
                                                     _get_program_options())


fp_option_functions = generate_option_functions(_get_fp_section_comments(),
                                                _get_fp_options())
