@echo off
@SETLOCAL

set Processor=%1

set CorrectArg=0

if [%1]==[] (
    echo The first Argument must be '32' or '64'
    exit /B

)




del .\build\wires_processor\* /q  >nul 2>&1

if %Processor% == 64 (

    echo 64 > build/processor_bits
    xcopy .\build\wires_processor_64 .\build\wires_processor /E >nul 2>&1
    set CorrectArg=1
    
    
    pyinstaller --distpath=.\bin\fixture_processor --onefile  --icon=assets\index.ico --noupx run.py
    
    :: make a copy of the build folder for quicker future builds.
    del .\build\wires_processor_64\* /q  >nul 2>&1
    
    xcopy .\build\wires_processor .\build\wires_processor_64 /E >nul 2>&1
    
)



if %Processor% == 32 (

    echo 32 > build/processor_bits
    xcopy .\build\wires_processor_32 .\build\wires_processor /E >nul 2>&1
    set CorrectArg=1

    SET "PATH=%localappdata%\Programs\Python\Python37-32"
    SET "PATH=%PATH%;%localappdata%\Programs\Python\Python37-32\Scripts"
    
    "%localappdata%\Programs\Python\Python37-32\Scripts\pyinstaller.exe" --distpath=.\bin\fixture_processor_x86 --onefile  --icon=assets\index.ico --noupx run.py
    
    
    del .\build\wires_processor_32\* /q  >nul 2>&1
    
    xcopy .\build\wires_processor .\build\wires_processor_32 /E >nul 2>&1
    
)

if %CorrectArg% == 0 (
    echo The first Argument must be '32' or '64'
)
