setlocal

@echo off
REM the password for isis\IBEXbuilder is contained in the BUILDERPW system environment variable on the build server
REM we map this early as some other stuff (e.g. CSS, DAE DLLs) is copied from \\isis\inst$ too during build 
net use p: /d
net use p: \\isis\inst$ /user:isis\IBEXbuilder %BUILDERPW%

subst q: /d
subst q: p:\Kits$\CompGroup\ICP

REM for create_icp_binaries
net use \\shadow.isis.cclrc.ac.uk /d
net use \\shadow.isis.cclrc.ac.uk /user:isis\IBEXbuilder %BUILDERPW%
@echo on

REM is previous system tests aborted, we may still have processes running
if exist "C:\Instrument\Apps\EPICS\stop_ibex_server.bat" (
    call "C:\Instrument\Apps\EPICS\stop_ibex_server.bat"
)
@taskkill /f /im javaw.exe /t
@taskkill /f /im pythonw.exe /t
@taskkill /f /im ibex-client.exe /t

@echo on

REM Delete simulated instrument
rd /S /Q "C:\data"
if exist "C:\data" (
    timeout /t 60 /nobreak >NUL
    rd /S /Q "C:\data"
)
mkdir "C:\data"

REM Install genie_python, deleting the old one first, and going back to the workspace that the installer moves from
rd /S /Q "C:\Instrument\Apps\Python\"
if exist "C:\Instrument\Apps\Python\" (
    timeout /t 10 /nobreak >NUL
    rd /S /Q "C:\Instrument\Apps\Python\"
)

cd %WORKSPACE%

REM Clean up the previous versions
rd /S /Q "C:\Instrument\Apps\EPICS\"
if exist "C:\Instrument\Apps\EPICS\" (
    timeout /t 10 /nobreak >NUL
    rd /S /Q "C:\Instrument\Apps\EPICS\"
)
if exist "C:\Instrument\Apps\EPICS\" (
    timeout /t 60 /nobreak >NUL
    rd /S /Q "C:\Instrument\Apps\EPICS\"
)

REM Clean up the previous version of the GUI
rd /S /Q "C:\Instrument\Apps\Client"
if exist "C:\Instrument\Apps\Client" (
    timeout /t 10 /nobreak >NUL
    rd /S /Q "C:\Instrument\Apps\Client"
)
REM Get the latest versions via a Python script
c:\Python27\python.exe get_latest_builds.py
if %errorlevel% neq 0 exit /b %errorlevel%

