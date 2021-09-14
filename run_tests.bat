setlocal
call create_virtual_env.bat
start /wait cmd /c %EPICS_ROOT%\stop_ibex_server.bat
python test_setup_teardown.py>base_line_memory.txt
set /P BASE_MEMORY_USAGE=<base_line_memory.txt
start /wait cmd /c %EPICS_ROOT%\start_ibex_server.bat
set "PYTHONUNBUFFERED=1"
set "exitcode=0"
python "%~dp0run_tests.py" %*
IF %errorlevel% NEQ 0 (
	set exitcode=%errorlevel%
    echo "running base tests failed."
	goto finish
)
call %EPICS_ROOT%\ISIS\JournalParser\master\test\run_tests.bat
IF %errorlevel% NEQ 0 (
    set exitcode=%errorlevel%
    echo "running journal tests failed."
    goto finish
)

:finish
python test_setup_teardown.py --tear_down
start /wait cmd /c %EPICS_ROOT%\stop_ibex_server.bat
EXIT /b %exitcode%
