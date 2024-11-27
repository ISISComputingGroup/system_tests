setlocal
call create_virtual_env.bat
call %EPICS_ROOT%\stop_ibex_server.bat

REM always run system tests against latest versions of genie_python and ibex_bluesky_core
python -m pip install genie_python[plot]@git+https://github.com/IsisComputingGroup/genie.git@main
if %errorlevel% NEQ 0 EXIT /B %errorlevel%
python -m pip install ibex_bluesky_core@git+https://github.com/IsisComputingGroup/ibex_bluesky_core.git@main
if %errorlevel% NEQ 0 EXIT /B %errorlevel%

python -u test_setup_teardown.py>base_line_memory.txt
set exitcode=%errorlevel%
IF %exitcode% NEQ 0 (
    echo ERROR: Running test_setup_teardown failed with code %exitcode%
)
set /P BASE_MEMORY_USAGE=<base_line_memory.txt
if "%EPICS_HOST_ARCH:~0,9%" == "win32-x86" (
    @echo Skipping first part as 32bit system %EPICS_HOST_ARCH%
    goto finish
)
call %EPICS_ROOT%\start_ibex_server.bat
set "PYTHONUNBUFFERED=1"
python -u "%~dp0run_tests.py" %*
IF %errorlevel% NEQ 0 (
    set exitcode=%errorlevel%
    echo ERROR: Running base tests failed with code %errorlevel%
    goto finish
)
call %EPICS_ROOT%\ISIS\JournalParser\master\test\run_tests.bat
IF %errorlevel% NEQ 0 (
    set exitcode=%errorlevel%
    echo ERROR: running journal tests failed with code %errorlevel%
    goto finish
)

:finish
python -u test_setup_teardown.py --tear_down
call %EPICS_ROOT%\stop_ibex_server.bat
EXIT /b %exitcode%
