
@echo off

set InitialPath=%PATH%

:: automatically format
:: autopep8 --in-place "./fixture_processor/__init__.py"
:: autopep8 --in-place "./fixture_processor/__main__.py"
:: autopep8 --in-place "./fixture_processor/file_operations.py"
:: autopep8 --in-place "./fixture_processor/fixture_processor_form.py"
:: autopep8 --in-place "./fixture_processor/helper_functions.py"
:: 
:: 
:: 
:: autopep8 --in-place "./fixture_processor/fixture_functions/extract_wires.py"
:: autopep8 --in-place "./fixture_processor/fixture_functions/fixture_input.py"
:: autopep8 --in-place "./fixture_processor/fixture_functions/fixture_maths.py"
:: autopep8 --in-place "./fixture_processor/fixture_functions/fixture_modifications.py"
:: autopep8 --in-place "./fixture_processor/fixture_functions/fixture_output.py"
:: autopep8 --in-place "./fixture_processor/fixture_functions/fixture_processing.py"
:: autopep8 --in-place "./fixture_processor/fixture_functions/output_data.py"
:: 
:: 
:: autopep8 --in-place "./fixture_processor/options_lib/__init__.py"
:: autopep8 --in-place "./fixture_processor/options_lib/options_functions.py"
:: autopep8 --in-place "./fixture_processor/options_lib/program_options.py"
:: autopep8 --in-place "./fixture_processor/options_lib/fixture_processing_options.py"

:: check code quality
::pylint fixture_processor > pylint_output.txt
::flake8 fixture_processor > flake8_output.txt
::
del .\build\wires_processor\* /q

pyinstaller --distpath=.\bin\fixture_processor --onefile  --noupx wires_processor.py

del .\build\wires_processor\* /q

SET PATH=C:\Users\Andrew Kenny\AppData\Local\Programs\Python\Python37-32
SET PATH=%PATH%;C:\Users\Andrew Kenny\AppData\Local\Programs\Python\Python37-32\Scripts



"C:\Users\Andrew Kenny\AppData\Local\Programs\Python\Python37-32\Scripts\pyinstaller.exe" --distpath=.\bin\fixture_processor_x86 --onefile  --noupx wires_processor.py

set PATH=%InitialPath%