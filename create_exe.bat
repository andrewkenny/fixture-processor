
@echo off

set InitialPath=%PATH%



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