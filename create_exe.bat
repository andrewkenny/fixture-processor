@echo off

set Processor=%1

set CorrectArg=0

echo %localappdata%


del .\build\wires_processor\* /q  >nul 2>&1

if %Processor% == 64 (

    set CorrectArg=1
    
    
    pyinstaller --distpath=.\bin\fixture_processor --onefile  --icon=assets\index.ico --noupx wires_processor.py

)

if %Processor% == 32 (
    set CorrectArg=1


    set InitialPath=%PATH%
    SET PATH=%localappdata%\Programs\Python\Python37-32
    SET PATH=%PATH%;%localappdata%\Programs\Python\Python37-32\Scripts
    
    "%localappdata%\Programs\Python\Python37-32\Scripts\pyinstaller.exe" --distpath=.\bin\fixture_processor_x86 --onefile  --icon=assets\index.ico --noupx wires_processor.py
    
    set PATH=%InitialPath%
)

if %CorrectArg% == 0 (
    echo The first Argument must be '32' or '64'
)
