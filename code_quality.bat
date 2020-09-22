
@echo off

:: check code quality
pylint fixture_processor > pylint_output.txt
flake8 fixture_processor > flake8_output.txt


mypy fixture_processor > mypy_output.txt
