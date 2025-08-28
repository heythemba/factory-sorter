@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM Usage: install_deps.bat [python_executable]
REM Examples:
REM   install_deps.bat py
REM   install_deps.bat python

set PYEXE=%1
if "%PYEXE%"=="" set PYEXE=py

where %PYEXE% >nul 2>nul
if errorlevel 1 (
  echo %PYEXE% not found in PATH. Trying python and python3...
  where python >nul 2>nul && set PYEXE=python
  if errorlevel 1 (
    where python3 >nul 2>nul && set PYEXE=python3
    if errorlevel 1 (
      echo No suitable Python executable found. Please install Python and add it to PATH.
      exit /b 1
    )
  )
)

REM Check pip; try ensurepip or bootstrap if needed
%PYEXE% -m pip --version >nul 2>nul
if errorlevel 1 (
  echo pip not found. Trying ensurepip...
  %PYEXE% -m ensurepip --upgrade
  if errorlevel 1 (
    echo ensurepip failed. Bootstrapping get-pip.py...
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py' -UseBasicParsing"
    %PYEXE% get-pip.py
    del get-pip.py
  )
)

%PYEXE% -m pip install --upgrade pip
%PYEXE% -m pip install -r requirements.txt

echo All dependencies installed successfully for %PYEXE%.
