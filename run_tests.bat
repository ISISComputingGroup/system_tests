setlocal
call create_virtual_env.bat
call %EPICS_ROOT%\stop_ibex_server.bat
"%PYTHON3%" test_setup_teardown.py>base_line_memory.txt
set /P BASE_MEMORY_USAGE=<base_line_memory.txt
call %EPICS_ROOT%\start_ibex_server.bat
set "PYTHONUNBUFFERED=1"
set "exitcode=0"

for /D %%I in ( "C:\Program Files (x86)\Windows Kits\*" ) do (
    if exist "%%I\Debuggers\x64\windbg.exe" SET "WINDBG=%%I\Debuggers\x64\windbg.exe"
)

REM disable windbg as non-interactive jenkins
if not "%WINDBG%" == "" (
    REM we use the python3 executable rather than python as this allows us to
    REM configure the applicatrion verifier for python3.exe and we don't get
    REM a lot of logs every time tests spawn python.exe for e.g. emulators
    REM "%WINDBG%" -g -xd av -xd ch -xd sov "c:\instrument\Apps\python3\python3.exe" -u "%~dp0run_tests.py" %*
    "c:\instrument\Apps\python3\python3.exe" -u "%~dp0run_tests.py" %*
) else (
    "%PYTHON3%" -u "%~dp0run_tests.py" %*
)
IF %errorlevel% NEQ 0 (
    set exitcode=%errorlevel%
    echo ERROR - Running base tests failed with code %errorlevel%
    goto finish
)
call %EPICS_ROOT%\ISIS\JournalParser\master\test\run_tests.bat
IF %errorlevel% NEQ 0 (
    set exitcode=%errorlevel%
    echo ERROR - running journal tests failed with code %errorlevel%
    goto finish
)

:finish
"%PYTHON3%" test_setup_teardown.py --tear_down
call %EPICS_ROOT%\stop_ibex_server.bat
EXIT /b %exitcode%
